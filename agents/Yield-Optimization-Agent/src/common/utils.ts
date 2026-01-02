/**
 * Common utility functions
 */

import { isAddress as viemIsAddress } from 'viem';

/**
 * Check if a string is a valid Ethereum address
 */
export function isAddress(address: string): boolean {
  return viemIsAddress(address);
}

/**
 * Format error message with context
 */
export function formatError(message: string, context?: Record<string, unknown>): string {
  if (!context || Object.keys(context).length === 0) {
    return message;
  }

  const contextStr = Object.entries(context)
    .map(([key, value]) => `${key}: ${value}`)
    .join(', ');

  return `${message} (${contextStr})`;
}

/**
 * Retry a function with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  initialDelay = 1000,
): Promise<T> {
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (attempt < maxRetries - 1) {
        const delay = initialDelay * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError || new Error('Retry failed');
}

/**
 * Retry a function with exponential backoff, but only for rate limit errors (429)
 * Other errors are thrown immediately without retry
 */
export async function retryOnRateLimit<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  initialDelay = 2000,
  logger?: { warn: (msg: string) => void; info: (msg: string) => void },
): Promise<T> {
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error as Error;
      const errorMessage = error?.message || String(error);
      const errorStatus = error?.status || error?.statusCode || error?.response?.status;
      
      // Check for rate limit/quota errors - be more specific
      // "quota" errors that say "exceeded your current quota" are usually billing issues, not retryable
      const isQuotaExceeded = errorMessage.includes("exceeded your current quota") ||
                              errorMessage.includes("check your plan and billing");
      
      // Rate limit errors that are retryable
      const isRateLimit = errorStatus === 429 || 
                         errorMessage.includes("rate limit") ||
                         (errorMessage.includes("429") && !isQuotaExceeded);

      if (isQuotaExceeded) {
        // Quota exceeded - this is a billing issue, don't retry
        logger?.warn(`Quota exceeded (billing issue detected). Attempt ${attempt + 1}/${maxRetries}. Not retrying.`);
        throw error;
      }

      if (!isRateLimit) {
        // Not a rate limit error, throw immediately
        throw error;
      }

      // Rate limit error - retry if we have attempts left
      if (attempt < maxRetries - 1) {
        const delay = initialDelay * Math.pow(2, attempt);
        logger?.info(`Rate limit detected (attempt ${attempt + 1}/${maxRetries}). Retrying in ${delay}ms...`);
        await new Promise((resolve) => setTimeout(resolve, delay));
      } else {
        logger?.warn(`Rate limit retries exhausted after ${maxRetries} attempts.`);
      }
    }
  }

  throw lastError || new Error('Retry failed');
}

