import { StateGraph, END } from "@langchain/langgraph";
import {
  perceptionNode,
  analystNode,
  protectionNode,
  therapistNode,
} from "./nodes";

export function createZenGuardWorkflow() {
  const workflow = new StateGraph<any>({
    channels: {
      messages: { reducer: (x: any, y: any) => x.concat(y), default: () => [] },
      metrics: { reducer: (x: any, y: any) => y ?? x, default: () => ({}) },
      interventionLevel: {
        reducer: (x: any, y: any) => y ?? x,
        default: () => "NONE",
      },
      forensicData: { reducer: (x: any, y: any) => y ?? x, default: () => "" },
      wardenIntent: {
        reducer: (x: any, y: any) => y ?? x,
        default: () => null,
      },
    },
  })
    .addNode("perception", perceptionNode)
    .addNode("analyst", analystNode)
    .addNode("protection", protectionNode)
    .addNode("therapist", therapistNode)

    .setEntryPoint("perception")

    // 1. Perception -> Analyst
    .addEdge("perception", "analyst")

    // 2. Analyst -> Conditional Edge
    .addConditionalEdges(
      "analyst",
      (state) => {
        if (state.interventionLevel === "HARD_LOCK") {
          return "protection";
        }
        return "therapist";
      },
      { protection: "protection", therapist: "therapist" },
    )

    // 3. Protection -> Therapist
    .addEdge("protection", "therapist")

    // 4. Therapist -> End
    .addEdge("therapist", END);

  return workflow.compile();
}

// Export compiled workflow instance for API use
export const zenGuardWorkflow = createZenGuardWorkflow();
