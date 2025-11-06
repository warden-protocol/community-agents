export type AgentResponse = {
  question: string;
  response: {
    messages: any[];
    structuredResponse: any;
  };
};
