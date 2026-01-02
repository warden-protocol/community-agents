/**
 * API Middleware
 * Request validation, error handling, etc.
 */

import { Request, Response, NextFunction } from "express";
import { z } from "zod";
import { Logger } from "../common/logger";

const logger = new Logger("API-Middleware");

/**
 * Validation middleware factory
 */
export function validateRequest(schema: z.ZodSchema) {
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      // Validate against schema
      const data = req.method === "GET" ? req.query : req.body;
      await schema.parseAsync(data);
      next();
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({
          success: false,
          error: "Validation error",
          details: error.errors.map((err) => ({
            field: err.path.join("."),
            message: err.message,
          })),
          timestamp: new Date().toISOString(),
        });
      } else {
        next(error);
      }
    }
  };
}

/**
 * Error handling middleware
 */
export function errorHandler(
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction
): void {
  logger.error(`Error handling ${req.method} ${req.path}:`, error);

  // Check if response already sent
  if (res.headersSent) {
    return next(error);
  }

  // Determine status code and message
  let statusCode = 500;
  let message = "Internal server error";
  let details: any = undefined;

  if (error.message.includes("OPENAI_API_KEY")) {
    statusCode = 503;
    message = "OpenAI API key not configured";
    details = "Server is not properly configured. Please contact the administrator.";
  } else if (error.message.includes("ENSO_API_KEY")) {
    statusCode = 503;
    message = "Enso API key not configured";
    details = "Server is not properly configured. Please contact the administrator.";
  } else if (error.message.includes("rate limit") || error.message.includes("429")) {
    statusCode = 429;
    message = "Rate limit exceeded";
    details = "Too many requests. Please try again later.";
  } else if (error.message.includes("not found")) {
    statusCode = 404;
    message = "Resource not found";
    details = error.message;
  } else if (error.message.includes("Invalid") || error.message.includes("validation")) {
    statusCode = 400;
    message = "Invalid request";
    details = error.message;
  }

  res.status(statusCode).json({
    success: false,
    error: message,
    details: details || (process.env.NODE_ENV === "development" ? error.message : undefined),
    timestamp: new Date().toISOString(),
    ...(process.env.NODE_ENV === "development" && {
      stack: error.stack,
    }),
  });
}

/**
 * Async handler wrapper to catch errors in async route handlers
 */
export function asyncHandler(
  fn: (req: Request, res: Response, next: NextFunction) => Promise<any>
) {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

