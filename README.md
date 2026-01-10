# Warden Community Agents

This is a collection of **Warden Community Agents and Tools** built with TypeScript or Python.

💫 The [Agent Builder Incentive Programme](https://wardenprotocol.org/blog/agent-builder-incentive-programme) is live! 
[Register now](https://docs.google.com/forms/d/e/1FAIpQLSdwTR0BL8-T3LLbJt6aIyjuEYjMAmJPMdwffwHcyW6gskDQsg/viewform) and get paid for building agents! Up to $10,000 in incentives for each agent in the Top 10 in the first month.

## 📚 Documentation

All documentation can be found in the [`docs/`](docs) directory.

If you get stuck or you need to get in touch, join the [`#developers`](https://discord.com/channels/1199357852666560654/1222892775876333629) channel on our [Discord server](https://discord.gg/wardenprotocol).

## 🤖 Example Agents

Each agent in the [`agents/`](agents) directory is completely self-sufficient and comes with its own:
- Dependencies and devDependencies
- Configuration files
- Build scripts
- Tests  (excluding starter templates)

## Available Agents

- **[langgraph-quick-start](agents/langgraph-quick-start)**: LangGraph starter template in TypeScript (easiest)
- **[langgraph-quick-start-py](agents/langgraph-quick-start-py)**: LangGraph starter template in Python (easiest)
- **[weather-agent](agents/weather-agent)**: Beginner-friendly weather agent (less complex) **<- recommended for new agent developers**
- **[coingecko-agent](agents/coingecko-agent)**: CoinGecko agent for cryptocurrency data analysis (more complex)
- **[portfolio-agent](agents/portfolio-agent)**: Portfolio agent for cryptocurrency wallet performance analysis (more complex)

## Requirements

When building your agent for the incentive programme, you can implement any Web3 or Web2 workflowand any custom functionality. Your Agent can connect to APIs, use databases, tools, and so on.

**To qualify for rewards**, please keep in mind the following requirements and technical limitations:

- At the moment, you must use [LangGraph](https://www.langchain.com/langgraph). Support for more frameworks is coming soon.
- You can deploy your Agent on LangGraph Cloud or on your own infrastructure ([learn more](docs/deploy-an-agent.md)).
- Make sure that your Agent is accessible through an API. **No UI is required**.
- Make sure that you only have one Agent per LangGraph instance to keep your Agents separated.
- For security reasons, Agents will not have access to users' wallets, nor will they be able to store any data on Warden infrastructure. These limitations will be removed in the next phase of Warden Agent Hub in the beginning of 2026.

> [!IMPORTANT]
> We'll soon launch **Warden Studio**—a platform where you can register and monetize your Agent. Once it's available, you'll be able to add your Agent directly there, providing just the following:
> - Your agent's API URL and API key
> - The name, description, and skills
> - The avatar


![Registering an Agent in Warden Studio](images/warden-studio.png)

## 🌟 Community Agents and Tools

Awesome agents and tools built by the community! Add yours by submitting a PR to this README file.

**Format:** `[Project Name](link): Short agent description`


### Agents

- [Travel DeFi Agent](https://github.com/Joshua15310/travel-defi-agent): LangGraph agent for travel planning and expense optimization using Gemini AI and DeFi strategies.

- [Cross-Chain Yield Intelligence Agent](https://github.com/rudazy/warden-yield-agent): AI agent that finds and ranks the best DeFi yield opportunities across 7 blockchain networks
- [Portfolio Manager Agent](https://github.com/0xnald/portfolio-manager-agent): AI-powered crypto portfolio agent that adapts allocations in real time based on market data and natural language inputs

### Tools & Resources

- [Your Tool](https://github.com/username/repo): Description of what your tool does
