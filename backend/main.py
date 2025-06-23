from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import uuid
import json
from datetime import datetime
import asyncio
from collections import defaultdict, deque
import openai
import os

app = FastAPI(title="Agentic Flow Orchestrator", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (replace with database in production)
flows_db = {}
executions_db = {}

# Pydantic models
class NodeData(BaseModel):
    id: str
    type: str
    position: Dict[str, float]
    data: Dict[str, Any]

class EdgeData(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None

class FlowData(BaseModel):
    id: str
    name: str
    nodes: List[NodeData]
    edges: List[EdgeData]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ExecutionResult(BaseModel):
    id: str
    flow_id: str
    status: str
    results: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

# Node implementations
class BaseNode:
    def __init__(self, node_id: str, data: Dict[str, Any]):
        self.id = node_id
        self.data = data
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class PromptNode(BaseNode):
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        template = self.data.get('template', '')
        variables = self.data.get('variables', {})
        
        # Replace variables in template
        result = template
        for key, value in variables.items():
            result = result.replace(f'{{{key}}}', str(value))
        
        # Replace with input values
        for key, value in inputs.items():
            result = result.replace(f'{{{key}}}', str(value))
        
        return {"output": result}

class FunctionNode(BaseNode):
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        function_code = self.data.get('code', 'return input_data')
        
        # Create a safe execution environment
        safe_globals = {
            '__builtins__': {
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'sum': sum,
                'max': max,
                'min': min,
            }
        }
        
        try:
            # Execute the function code
            exec(f"def user_function(input_data, inputs):\n    {function_code}", safe_globals)
            result = safe_globals['user_function'](inputs.get('input', ''), inputs)
            return {"output": result}
        except Exception as e:
            return {"output": f"Error: {str(e)}"}

class LLMNode(BaseNode):
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        prompt = inputs.get('prompt', self.data.get('prompt', ''))
        model = self.data.get('model', 'gpt-3.5-turbo')
        
        # Mock LLM response (replace with actual LLM call)
        if os.getenv('OPENAI_API_KEY'):
            try:
                client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=150
                )
                result = response.choices[0].message.content
            except Exception as e:
                result = f"LLM Error: {str(e)}"
        else:
            result = f"Mock LLM response for: {prompt}"
        
        return {"output": result}

class StartNode(BaseNode):
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"output": self.data.get('initialValue', 'Started')}

class EndNode(BaseNode):
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return {"output": inputs.get('input', 'Completed')}

# Flow execution engine
class FlowEngine:
    def __init__(self):
        self.node_types = {
            'prompt': PromptNode,
            'function': FunctionNode,
            'llm': LLMNode,
            'start': StartNode,
            'end': EndNode
        }
    
    def build_graph(self, nodes: List[NodeData], edges: List[EdgeData]):
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        node_map = {node.id: node for node in nodes}
        
        for edge in edges:
            graph[edge.source].append(edge.target)
            in_degree[edge.target] += 1
        
        # Ensure all nodes are in in_degree
        for node in nodes:
            if node.id not in in_degree:
                in_degree[node.id] = 0
        
        return graph, in_degree, node_map
    
    def topological_sort(self, graph, in_degree):
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node = queue.popleft()
            result.append(node)
            
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    async def execute_flow(self, flow: FlowData) -> Dict[str, Any]:
        graph, in_degree, node_map = self.build_graph(flow.nodes, flow.edges)
        execution_order = self.topological_sort(graph, in_degree)
        
        results = {}
        node_outputs = {}
        
        for node_id in execution_order:
            node_data = node_map[node_id]
            node_class = self.node_types.get(node_data.type)
            
            if not node_class:
                results[node_id] = {"error": f"Unknown node type: {node_data.type}"}
                continue
            
            node = node_class(node_id, node_data.data)
            
            # Gather inputs from predecessor nodes
            inputs = {}
            for edge in flow.edges:
                if edge.target == node_id and edge.source in node_outputs:
                    inputs[edge.sourceHandle or 'input'] = node_outputs[edge.source]
            
            # Execute node
            try:
                output = await node.execute(inputs)
                node_outputs[node_id] = output.get('output', output)
                results[node_id] = output
            except Exception as e:
                results[node_id] = {"error": str(e)}
        
        return results

# Initialize flow engine
flow_engine = FlowEngine()

# API endpoints
@app.get("/")
async def root():
    return {"message": "Agentic Flow Orchestrator API"}

@app.get("/flows")
async def get_flows():
    return {"flows": list(flows_db.values())}

@app.post("/flows")
async def create_flow(flow: FlowData):
    flow.id = str(uuid.uuid4())
    flow.created_at = datetime.now()
    flow.updated_at = datetime.now()
    flows_db[flow.id] = flow
    return flow

@app.get("/flows/{flow_id}")
async def get_flow(flow_id: str):
    if flow_id not in flows_db:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flows_db[flow_id]

@app.put("/flows/{flow_id}")
async def update_flow(flow_id: str, flow: FlowData):
    if flow_id not in flows_db:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    flow.id = flow_id
    flow.updated_at = datetime.now()
    flows_db[flow_id] = flow
    return flow

@app.delete("/flows/{flow_id}")
async def delete_flow(flow_id: str):
    if flow_id not in flows_db:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    del flows_db[flow_id]
    return {"message": "Flow deleted successfully"}

@app.post("/flows/{flow_id}/execute")
async def execute_flow(flow_id: str):
    if flow_id not in flows_db:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    flow = flows_db[flow_id]
    execution_id = str(uuid.uuid4())
    
    execution = ExecutionResult(
        id=execution_id,
        flow_id=flow_id,
        status="running",
        results={},
        started_at=datetime.now()
    )
    
    executions_db[execution_id] = execution
    
    try:
        results = await flow_engine.execute_flow(flow)
        execution.results = results
        execution.status = "completed"
        execution.completed_at = datetime.now()
    except Exception as e:
        execution.error = str(e)
        execution.status = "failed"
        execution.completed_at = datetime.now()
    
    executions_db[execution_id] = execution
    return execution

@app.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    if execution_id not in executions_db:
        raise HTTPException(status_code=404, detail="Execution not found")
    return executions_db[execution_id]

@app.get("/flows/{flow_id}/executions")
async def get_flow_executions(flow_id: str):
    executions = [exec for exec in executions_db.values() if exec.flow_id == flow_id]
    return {"executions": executions}

# Node types endpoint for frontend
@app.get("/node-types")
async def get_node_types():
    return {
        "nodeTypes": [
            {
                "type": "start",
                "label": "Start",
                "description": "Starting point of the flow",
                "inputs": [],
                "outputs": ["output"]
            },
            {
                "type": "prompt",
                "label": "Prompt",
                "description": "Text prompt with variable substitution",
                "inputs": ["input"],
                "outputs": ["output"]
            },
            {
                "type": "function",
                "label": "Function",
                "description": "Custom Python function",
                "inputs": ["input"],
                "outputs": ["output"]
            },
            {
                "type": "llm",
                "label": "LLM",
                "description": "Large Language Model call",
                "inputs": ["prompt"],
                "outputs": ["output"]
            },
            {
                "type": "end",
                "label": "End",
                "description": "End point of the flow",
                "inputs": ["input"],
                "outputs": []
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
