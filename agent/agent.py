from agents import Agent, Runner, function_tool
from agents.mcp import MCPServer 
from utils.logger import InteractionLogger
from utils.config import Config

class TourismAgent:
    def __init__(self):
        self.config = Config()
        self.logger = InteractionLogger(self.config.LOG_PATH)
        self.mcp_servers = []
        self.loaded_skills = set()
        
        # Initialize MCP Servers
        self._init_mcp_servers()
        
        # Load available skills metadata
        self.skills_system_prompt = self._load_skills_system_prompt()
        
        # Initialize the OpenAI Agent
        self.agent = Agent(
            name="TourismAnalyst",
            instructions=f"""你是一个旅游业发展分析专家。
            
            {self.skills_system_prompt}
            
            当用户提问时，请遵循ReAct（思考-行动-观察）的模式。
            1. 检查可用技能。
            2. 如果需要某个技能，调用 `load_skill` 加载它。
            3. 阅读加载的技能说明，并按说明调用相应的工具。
            """,
            tools=[self.load_skill], # Pass load_skill as a tool
            mcp_servers=self.mcp_servers, # Pass MCP server instances directly
            model="gpt-4o" # Or appropriate model
        )
        
        self.logger.log_interaction("system", "agent", "initialized", "Agent initialized with MCP servers and skills")

    def _init_mcp_servers(self):
        """Initialize connections to MCP servers."""
        try:
            # Connect to Tourism Query Server
            tourism_server = MCPServer(
                name="tourism_query",
                url=self.config.MCP_TOURISM_QUERY_URL
            )
            self.mcp_servers.append(tourism_server)
            
            # Connect to Deep Analysis Server
            deep_server = MCPServer(
                name="deep_analysis",
                url=self.config.MCP_DEEP_ANALYSIS_URL
            )
            self.mcp_servers.append(deep_server)
            
            self.logger.log_interaction("agent", "mcp_servers", "connected", f"Connected to {len(self.mcp_servers)} MCP servers")
        except Exception as e:
            self.logger.log_interaction("agent", "system", "error", f"Failed to connect to MCP servers: {e}")

    def _load_skills_system_prompt(self) -> str:
        """Read the AGENTS.md content."""
        agents_file = os.path.join(self.config.SKILLS_PATH, "AGENTS.md")
        if os.path.exists(agents_file):
            with open(agents_file, "r", encoding="utf-8") as f:
                return f.read()
        return "No skills available."

    @function_tool
    def load_skill(self, skill_name: str) -> str:
        """
        Load a skill's detailed instructions by name.
        Use this tool when you identify a relevant skill in the <available_skills> list.
        """
        self.logger.log_interaction("agent", "skill_manager", f"loading_skill: {skill_name}")
        
        if skill_name in self.loaded_skills:
            return f"Skill '{skill_name}' is already loaded."
            
        skill_path = os.path.join(self.config.SKILLS_PATH, skill_name, "SKILL.md")
        if os.path.exists(skill_path):
            with open(skill_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            self.loaded_skills.add(skill_name)
            self.logger.log_interaction("skill_manager", "agent", f"loaded content for {skill_name}")
            return f"Instructions for skill '{skill_name}':\n\n{content}"
        else:
            return f"Skill '{skill_name}' not found."

    async def process_query(self, query: str):
        """Process a user query using the Runner."""
        self.logger.log_interaction("user", "agent", query)
        
        result = await Runner.run(self.agent, input=query)
        
        self.logger.log_interaction("agent", "user", result.final_output)
        return result.final_output

