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

## Requirements and Limitations

When building your agent for the incentive programme, please keep in mind the following requirements and technical limitations:

- Make sure that your agent is accessible through an API. **No UI is required**.
- At the moment, you can use only [LangGraph](https://www.langchain.com/langgraph). However, support for more agent frameworks is coming soon.
- Make sure that you only have **one agent per LangGraph instance** to keep your agents separated.
- For security reasons, agents will not have access to users' wallets in the beginning, nor will they be able to store any data on Warden infrastructure.

We'll soon launch our developer toolkit, **Warden Studio**. Once it's available, you'll be able to register your Agent directly through the Studio, providing just the following:

- Your agent's API URL and API key
- The name, description, and skills
- The avatar

## 🌟 Community Agents and Tools

Awesome agents and tools built by the community! Add yours by submitting a PR to this README file.

**Format:** `[Project Name](link): Short agent description`


### Agents

- [Travel DeFi Agent](https://github.com/Joshua15310/travel-defi-agent): LangGraph agent for travel planning and expense optimization using Gemini AI and DeFi strategies.

### Tools & Resources

- [Your Tool](https://github.com/username/repo): Description of what your tool does
