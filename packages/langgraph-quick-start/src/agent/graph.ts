import { StateGraph } from "@langchain/langgraph";
import { RunnableConfig } from "@langchain/core/runnables";
import { StateAnnotation } from "./state.js";
import { ChatOpenAI } from "@langchain/openai";
import { HumanMessage } from "@langchain/core/messages";

/**
 * Define a node, these do the work of the graph and should have most of the logic.
 * Must return a subset of the properties set in StateAnnotation.
 * @param state The current state of the graph.
 * @param config Extra parameters passed into the state graph.
 * @returns Some subset of parameters of the graph state, used to update the state
 * for the edges and nodes executed next.
 */
const callModel = async (
  state: typeof StateAnnotation.State,
  _config: RunnableConfig,
): Promise<typeof StateAnnotation.Update> => {
  const model = new ChatOpenAI({
    modelName: "gpt-4o-mini",
    temperature: 0.7,
    apiKey: process.env.OPENAI_API_KEY,
  });

  const response = await model.invoke([
    {
      role: "system",
      content: "You are a helpful assistant that only answers questions about crypto."
    },
    new HumanMessage(state.messages[0].content),
  ]);

  console.log("Model response:", response);

  return {
    messages: [
      {
        role: "assistant",
        content: response.content,
      },
    ],
  };
};
/**
 * Routing function: Determines whether to continue research or end the builder.
 * This function decides if the gathered information is satisfactory or if more research is needed.
 *
 * @param state - The current state of the research builder
 * @returns Either "callModel" to continue research or END to finish the builder
 */
export const route = (
  state: typeof StateAnnotation.State,
): "__end__" | "callModel" => {
  if (state.messages.length > 0) {
    return "__end__";
  }
  return "callModel";
};

// Finally, create the graph itself.
const builder = new StateGraph(StateAnnotation)
  // Add the nodes to do the work.
  // Chaining the nodes together in this way
  // updates the types of the StateGraph instance
  // so you have static type checking when it comes time
  // to add the edges.
  .addNode("callModel", callModel)
  // Regular edges mean "always transition to node B after node A is done"
  // The "__start__" and "__end__" nodes are "virtual" nodes that are always present
  // and represent the beginning and end of the builder.
  .addEdge("__start__", "callModel")
  // Conditional edges optionally route to different nodes (or end)
  .addConditionalEdges("callModel", route);

export const graph = builder.compile();
graph.name = "New Agent";