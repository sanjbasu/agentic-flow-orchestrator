# Agentic Flow Orchestrator

A no-code visual workflow builder similar to n8n, built with FastAPI and React. Create, execute, and manage complex workflows using a drag-and-drop interface.

## Features

- **Visual Flow Builder**: Drag-and-drop interface for creating workflows
- **Multiple Node Types**: 
  - Start/End nodes for flow control
  - Prompt nodes for text templating
  - Function nodes for custom Python code
  - LLM nodes for AI integrations
- **Flow Execution**: Sequential and topological execution of workflows
- **Real-time Monitoring**: Track execution status and results
- **Dockerized Deployment**: Easy deployment with Docker Compose
- **OCI Ready**: Deployment scripts for Oracle Cloud Infrastructure

## Architecture

```
├── backend/          # FastAPI backend
│   ├── main.py      # Main application and API routes
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/         # React frontend
│   ├── src/
│   │   └── App.js   # Main React application
│   ├── package.json
│   └── Dockerfile
├── nginx/           # Nginx configuration
├── docker-compose.yml
└── deploy-oci.sh    # OCI deployment script
```

## Quick Start

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd agentic-flow-orchestrator
```

2. **Start with Docker Compose**
```bash
docker-compose up -d
```

3. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Manual Setup

#### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## Usage

### Creating a Flow

1. **Add Nodes**: Drag nodes from the sidebar to the canvas
2. **Configure Nodes**: Click "Edit" on any node to configure its properties
3. **Connect Nodes**: Drag from output handles (green) to input handles (blue)
4. **Save Flow**: Click "Save Flow" to persist your workflow
5. **Execute Flow**: Click "Execute Flow" to run the workflow

### Node Types

#### Start Node
- **Purpose**: Entry point for the workflow
- **Configuration**: Initial value to pass to the next node
- **Outputs**: `output`

#### Prompt Node
- **Purpose**: Text templating with variable substitution
- **Configuration**: Template string with `{variable}` placeholders
- **Inputs**: Variables and input data
- **Outputs**: `output` (processed template)

#### Function Node
- **Purpose**: Execute custom Python code
- **Configuration**: Python code snippet
- **Inputs**: `input_data` and `inputs` dictionary
- **Outputs**: `output` (return value of the function)
- **Example**:
```python
# Simple transformation
result = input_data.upper()
return result

# Using inputs
name = inputs.get('name', 'World')
return f"Hello, {name}!"
```

#### LLM Node
- **Purpose**: Call Large Language Models
- **Configuration**: Model selection (GPT-3.5, GPT-4)
- **Inputs**: `prompt`
- **Outputs**: `output` (LLM response)
- **Note**: Requires `OPENAI_API_KEY` environment variable

#### End Node
- **Purpose**: Workflow termination point
- **Inputs**: Final result data
- **Outputs**: None

## API Endpoints

### Flows
- `GET /flows` - List all flows
- `POST /flows` - Create a new flow
- `GET /flows/{flow_id}` - Get specific flow
- `PUT /flows/{flow_id}` - Update flow
- `DELETE /flows/{flow_id}` - Delete flow

### Execution
- `POST /flows/{flow_id}/execute` - Execute a flow
- `GET /executions/{execution_id}` - Get execution status
- `GET /flows/{flow_id}/executions` - Get flow execution history

### Metadata
- `GET /node-types` - Get available node types

## Deployment

### Docker Compose (Recommended)

```bash
# Development
docker-compose up -d

# Production
docker-compose --profile production up -d
```

### Oracle Cloud Infrastructure (OCI)

1. **Set up OCI CLI** and configure authentication
2. **Set environment variables**:
```bash
export OCI_COMPARTMENT_ID="ocid1.compartment.oc1..."
export OCI_SUBNET_ID="ocid1.subnet.oc1..."
export OCI_AVAILABILITY_DOMAIN="AD-1"
export OPENAI_API_KEY="your-openai-key" # Optional
```

3. **Run deployment script**:
```bash
chmod +x deploy-oci.sh
./deploy-oci.sh deploy
```

4. **Access the application** at the provided IP address

## Configuration

### Environment Variables

#### Backend
- `OPENAI_API_KEY`: OpenAI API key for LLM nodes (optional)

#### Frontend
- `REACT_APP_API_BASE_URL`: Backend API URL (default: http://localhost:8000)

### Production Considerations

1. **Database**: Replace in-memory storage with PostgreSQL or MongoDB
2. **Authentication**: Add user authentication and authorization
3. **Security**: Implement proper security headers and CORS policies
4. **Monitoring**: Add logging, metrics, and health checks
5. **Scaling**: Use load balancers and multiple instances

## Development

### Project Structure

```
agentic-flow-orchestrator/
├── backend/
│   ├── main.py              # FastAPI app with API routes
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile          # Backend container
├── frontend/
│   ├── src/
│   │   └── App.js          # React app with flow editor
│   ├── package.json        # Node.js dependencies
│   └── Dockerfile          # Frontend container
├── nginx/
│   └── nginx.conf          # Nginx configuration
├── docker-compose.yml      # Local development setup
├── deploy-oci.sh          # OCI deployment script
└── README.md              # This file
```

### Adding New Node Types

1. **Backend**: Add node class in `main.py`
```python
class CustomNode(BaseNode):
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Your custom logic here
        return {"output": "result"}
```

2. **Register node type**:
```python
self.node_types['custom'] = CustomNode
```

3. **Add to node types endpoint**:
```python
{
    "type": "custom",
    "label": "Custom Node",
    "description": "Your custom node description",
    "inputs": ["input"],
    "outputs": ["output"]
}
```

4. **Frontend**: Add configuration UI in the `CustomNode` component

### Testing

```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
npm test
```

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure backend CORS is configured for your frontend URL
2. **Node Execution Fails**: Check node configuration and input data
3. **LLM Nodes Not Working**: Verify `OPENAI_API_KEY` is set
4. **Docker Issues**: Ensure Docker and Docker Compose are installed

### Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs backend
docker-compose logs frontend
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation at `/docs`
3. Create an issue in the repository

