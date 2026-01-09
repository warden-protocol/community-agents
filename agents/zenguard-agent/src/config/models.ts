import { ChatOpenAI } from "@langchain/openai";
import { ChatAnthropic } from "@langchain/anthropic";
import dotenv from "dotenv";

dotenv.config();

// Router & Perception (Switched to GPT-4o for stability)
// Previously Google Gemini, but switched to avoid API versioning 404 errors during demo
export const routerModel = new ChatOpenAI({
  modelName: "gpt-4o",
  temperature: 0,
  apiKey: process.env.OPENAI_API_KEY,
});

// Forensic Analyst (Claude 3.5 Sonnet)
export const analystModel = new ChatAnthropic({
  modelName: "claude-3-5-sonnet-20240620",
  temperature: 0.1,
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// Therapist (GPT-4o)
export const therapistModel = new ChatOpenAI({
  modelName: "gpt-4o",
  temperature: 0.8,
  apiKey: process.env.OPENAI_API_KEY,
});
