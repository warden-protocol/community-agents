import { DynamicStructuredTool } from 'langchain/tools';
import { Tool } from '@modelcontextprotocol/sdk/types.js';
import z from 'zod';

export function convertCGToolToDynamicTool(
  cgTool: Tool,
  handler: (input: Record<string, any>) => Promise<any>,
) {
  return new DynamicStructuredTool({
    name: cgTool.name,
    description: cgTool.description,
    schema: z.object(
      Object.fromEntries(
        Object.entries(cgTool.inputSchema.properties).map(
          ([key, value]: [string, any]) => {
            let zodType: z.ZodTypeAny;

            if (value.type === 'string') {
              if (value.enum) {
                zodType = z.enum(value.enum as [string, ...string[]]);
              } else {
                zodType = z.string();
              }
            } else if (value.type === 'number') {
              zodType = z.number();
            } else if (value.type === 'boolean') {
              zodType = z.boolean();
            } else {
              zodType = z.any();
            }

            if (value.description) {
              zodType = zodType.describe(value.description);
            }

            // Make optional if not in required array
            if (!cgTool.inputSchema.required?.includes(key)) {
              zodType = zodType.optional();
            }

            return [key, zodType];
          },
        ),
      ),
    ),
    func: handler,
  });
}
