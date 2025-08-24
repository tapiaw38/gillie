import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.core.platform.functions.function_executor import (
    GenericFunctionExecutor,
    GenericHTTPTool,
    FunctionDefinition
)
from src.core.platform.config.service import ConfigurationService
from src.core.domain.model import Profile


class TestFunctionDefinition:
    def test_function_definition_creation(self):
        """Test creating a FunctionDefinition"""
        func_def = FunctionDefinition(
            name="test_function",
            description="Test description",
            url_template="https://api.test.com/endpoint?param={param}",
            method="GET",
            required_params=["param"],
            param_types={"param": "string"},
            param_descriptions={"param": "Test parameter"}
        )
        
        assert func_def.name == "test_function"
        assert func_def.description == "Test description"
        assert func_def.url_template == "https://api.test.com/endpoint?param={param}"
        assert func_def.method == "GET"
        assert func_def.required_params == ["param"]
        assert func_def.param_types == {"param": "string"}


class TestGenericHTTPTool:
    def test_tool_creation(self):
        """Test creating a GenericHTTPTool"""
        func_def = FunctionDefinition(
            name="test_tool",
            description="Test tool",
            url_template="https://api.test.com/endpoint?param={param}",
            required_params=["param"]
        )
        
        tool = GenericHTTPTool(func_def)
        assert tool.name == "test_tool"
        assert tool.description == "Test tool"
        assert tool.url_template == "https://api.test.com/endpoint?param={param}"
        assert tool.required_params == ["param"]
    
    @patch('requests.request')
    def test_tool_sync_execution_success(self, mock_request):
        """Test successful synchronous tool execution"""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.content = b'{"result": "success"}'
        mock_request.return_value = mock_response
        
        func_def = FunctionDefinition(
            name="test_tool",
            description="Test tool",
            url_template="https://api.test.com/endpoint?param={param}",
            required_params=["param"]
        )
        
        tool = GenericHTTPTool(func_def)
        result = tool._run(param="test_value")
        
        assert "Function executed successfully" in result
        mock_request.assert_called_once()
    
    def test_tool_missing_parameters(self):
        """Test tool execution with missing parameters"""
        func_def = FunctionDefinition(
            name="test_tool",
            description="Test tool",
            url_template="https://api.test.com/endpoint?param={param}",
            required_params=["param"]
        )
        
        tool = GenericHTTPTool(func_def)
        result = tool._run()  # No parameters provided
        
        assert "Missing required parameters" in result
        assert "param" in result


class TestGenericFunctionExecutor:
    @pytest.fixture
    def mock_config_service(self):
        """Mock configuration service"""
        config = Mock(spec=ConfigurationService)
        config.openai_config.api_key = "test_key"
        config.openai_config.base_url = "https://api.openai.com"
        config.openai_config.model = "gpt-3.5-turbo"
        return config
    
    @pytest.fixture
    def mock_profile(self):
        """Mock profile with functions"""
        profile = Mock(spec=Profile)
        profile.user_id = "test_user"
        profile.functions = [
            {
                "name": "test_function",
                "description": "Test function",
                "url": "https://api.test.com/endpoint?param={param}",
                "method": "GET"
            }
        ]
        return profile
    
    @patch('langchain.chat_models.ChatOpenAI')
    @patch('langchain.agents.create_openai_functions_agent')
    @patch('langchain.agents.AgentExecutor')
    def test_executor_initialization(self, mock_agent_executor, mock_create_agent, mock_chat_openai, mock_config_service):
        """Test executor initialization"""
        executor = GenericFunctionExecutor(mock_config_service)
        
        assert executor.config_service == mock_config_service
        assert executor.tools == []
        assert executor.agent is None
        assert executor.executor is None
    
    def test_create_tools_from_profile(self, mock_config_service, mock_profile):
        """Test creating tools from profile configuration"""
        executor = GenericFunctionExecutor(mock_config_service)
        tools = executor._create_tools_from_profile(mock_profile)
        
        assert len(tools) == 1
        assert isinstance(tools[0], GenericHTTPTool)
        assert tools[0].name == "test_function"
    
    def test_create_tools_from_profile_no_functions(self, mock_config_service):
        """Test creating tools from profile without functions"""
        profile = Mock(spec=Profile)
        profile.functions = None
        
        executor = GenericFunctionExecutor(mock_config_service)
        tools = executor._create_tools_from_profile(profile)
        
        assert tools == []
    
    def test_create_tools_from_profile_invalid_config(self, mock_config_service):
        """Test creating tools from profile with invalid configuration"""
        profile = Mock(spec=Profile)
        profile.functions = "invalid_json"
        
        executor = GenericFunctionExecutor(mock_config_service)
        tools = executor._create_tools_from_profile(profile)
        
        assert tools == []
    
    def test_infer_param_types(self, mock_config_service):
        """Test parameter type inference"""
        executor = GenericFunctionExecutor(mock_config_service)
        
        params = ["latitude", "longitude", "city", "date", "unknown_param"]
        param_types = executor._infer_param_types(params, {})
        
        assert param_types["latitude"] == "float"
        assert param_types["longitude"] == "float"
        assert param_types["city"] == "string"
        assert param_types["date"] == "string"
        assert param_types["unknown_param"] == "string"
    
    def test_create_param_descriptions(self, mock_config_service):
        """Test parameter description creation"""
        executor = GenericFunctionExecutor(mock_config_service)
        
        params = ["latitude", "city", "unknown_param"]
        descriptions = executor._create_param_descriptions(params, {})
        
        assert "Latitud en formato decimal" in descriptions["latitude"]
        assert "Nombre de la ciudad" in descriptions["city"]
        assert "Valor para el parámetro unknown_param" in descriptions["unknown_param"]
    
    @patch('langchain.agents.create_openai_functions_agent')
    @patch('langchain.agents.AgentExecutor')
    def test_setup_for_profile(self, mock_agent_executor, mock_create_agent, mock_config_service, mock_profile):
        """Test setting up executor for a specific profile"""
        executor = GenericFunctionExecutor(mock_config_service)
        executor.setup_for_profile(mock_profile)
        
        assert len(executor.tools) == 1
        assert executor.agent is not None
        assert executor.executor is not None
    
    @patch('langchain.agents.create_openai_functions_agent')
    @patch('langchain.agents.AgentExecutor')
    @patch.object(GenericFunctionExecutor, 'setup_for_profile')
    async def test_execute_function_success(self, mock_setup, mock_config_service, mock_profile):
        """Test successful function execution"""
        executor = GenericFunctionExecutor(mock_config_service)
        
        # Mock the executor
        mock_executor = AsyncMock()
        mock_executor.ainvoke.return_value = {"output": "Function executed successfully"}
        executor.executor = mock_executor
        executor.tools = [Mock()]
        
        result = await executor.execute_function(
            user_message="Test message",
            profile=mock_profile,
            chat_history=["Previous message"]
        )
        
        assert result == "Function executed successfully"
        mock_executor.ainvoke.assert_called_once()
    
    @patch('langchain.agents.create_openai_functions_agent')
    @patch('langchain.agents.AgentExecutor')
    async def test_execute_function_no_tools(self, mock_agent_executor, mock_create_agent, mock_config_service, mock_profile):
        """Test function execution when no tools are available"""
        executor = GenericFunctionExecutor(mock_config_service)
        
        result = await executor.execute_function(
            user_message="Test message",
            profile=mock_profile
        )
        
        assert "No functions are currently available" in result
    
    def test_get_available_functions(self, mock_config_service):
        """Test getting information about available functions"""
        executor = GenericFunctionExecutor(mock_config_service)
        
        # Create a mock tool
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test description"
        mock_tool.required_params = ["param1"]
        mock_tool.param_types = {"param1": "string"}
        mock_tool.param_descriptions = {"param1": "Test param"}
        
        executor.tools = [mock_tool]
        
        functions_info = executor.get_available_functions()
        
        assert len(functions_info) == 1
        assert functions_info[0]["name"] == "test_tool"
        assert functions_info[0]["description"] == "Test description"
        assert functions_info[0]["required_params"] == ["param1"]


# Integration tests
class TestFunctionExecutorIntegration:
    @pytest.fixture
    def sample_function_config(self):
        """Sample function configuration for testing"""
        return {
            "name": "weather_function",
            "description": "Get weather information",
            "url": "https://api.weather.com/current?lat={latitude}&lon={longitude}",
            "method": "GET",
            "examples": ["What's the weather like?"],
            "keywords": ["weather", "climate"]
        }
    
    def test_function_definition_from_config(self, sample_function_config):
        """Test creating FunctionDefinition from configuration"""
        executor = GenericFunctionExecutor(Mock())
        
        # Extract required parameters from URL template
        import re
        url_template = sample_function_config["url"]
        required_params = re.findall(r"\{(\w+)\}", url_template)
        
        assert "latitude" in required_params
        assert "longitude" in required_params
        assert len(required_params) == 2
    
    def test_tool_creation_workflow(self, sample_function_config):
        """Test the complete workflow of creating a tool"""
        executor = GenericFunctionExecutor(Mock())
        
        # Create tool from config
        tool = executor._create_tool_from_config(sample_function_config)
        
        assert tool is not None
        assert isinstance(tool, GenericHTTPTool)
        assert tool.name == "weather_function"
        assert tool.description == "Get weather information"
        assert tool.url_template == "https://api.weather.com/current?lat={latitude}&lon={longitude}"
        assert tool.method == "GET"
        assert "latitude" in tool.required_params
        assert "longitude" in tool.required_params


if __name__ == "__main__":
    pytest.main([__file__])





