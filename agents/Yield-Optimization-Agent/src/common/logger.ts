/**
 * Logger utility for consistent logging across the agent
 */

export class Logger {
  constructor(private name: string) {}

  info(message: string, ...args: unknown[]): void {
    console.log(`[${this.name}] INFO: ${message}`, ...args);
  }

  error(message: string, ...args: unknown[]): void {
    console.error(`[${this.name}] ERROR: ${message}`, ...args);
  }

  warn(message: string, ...args: unknown[]): void {
    console.warn(`[${this.name}] WARN: ${message}`, ...args);
  }

  debug(message: string, ...args: unknown[]): void {
    if (process.env.DEBUG === 'true') {
      console.debug(`[${this.name}] DEBUG: ${message}`, ...args);
    }
  }
}

