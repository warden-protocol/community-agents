import { z } from 'zod';

export const ResponseSchema = z.object({
  answer: z
    .string()
    .describe(
      'A natural language response to the user question about weather, including all relevant information.',
    ),
  location: z
    .string()
    .describe('The location the weather information is about.'),
  summary: z
    .string()
    .describe('A brief summary of the weather conditions or forecast.'),
  recommendations: z
    .array(z.string())
    .describe(
      'List of helpful recommendations based on the weather (e.g., what to wear, activities to do/avoid).',
    ),
  data_source: z
    .string()
    .describe(
      'Indication of what data was used to answer the question (e.g., "current weather", "3-day forecast").',
    ),
});

export type ResponseType = z.infer<typeof ResponseSchema>;
