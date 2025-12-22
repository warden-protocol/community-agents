import { z } from 'zod';

export const ResponseSchema = z.object({
  answer: z.string().describe('The main answer to the user question'),
  fundingData: z
    .array(
      z.object({
        token: z.string().describe('Token symbol'),
        fundingRate: z.number().describe('Current funding rate'),
        apr: z.number().describe('Annualized funding rate as APR percentage'),
      }),
    )
    .optional()
    .describe('Funding rate data if applicable'),
  analysis: z
    .string()
    .optional()
    .describe('Additional analysis or insights about the funding rates'),
  confidence: z
    .enum(['high', 'medium', 'low'])
    .describe('Confidence level of the response'),
});

export type AgentResponseSchema = z.infer<typeof ResponseSchema>;
