import fs from 'node:fs';

const resultDir = 'outputs';

export function writeAgentResult(
  timestamp: number,
  model: string,
  results: any,
): void {
  if (!fs.existsSync(resultDir)) {
    fs.mkdirSync(resultDir);
  }
  fs.writeFileSync(
    `${resultDir}/${timestamp}-${model}.json`,
    JSON.stringify(results, null, 2),
    'utf8',
  );
}
