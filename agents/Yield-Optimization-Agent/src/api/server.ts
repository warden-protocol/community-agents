/**
 * REST API Server for Yield Optimization Agent
 * Provides HTTP endpoints for accessing agent functionality
 */

import express, { Express, Request, Response, NextFunction } from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import dotenv from "dotenv";
import swaggerUi from "swagger-ui-express";
import { fileURLToPath } from "url";
import { swaggerSpec } from "./swagger";
import { router } from "./routes";
import { errorHandler } from "./middleware";
import { Logger } from "../common/logger";

// Load environment variables
dotenv.config();

const logger = new Logger("API-Server");

/**
 * Create and configure Express application
 */
export function createApp(): Express {
  const app = express();

  // Security middleware
  app.use(helmet({
    contentSecurityPolicy: false, // Disable for Swagger UI to work properly
  }));

  // CORS configuration
  app.use(
    cors({
      origin: process.env.CORS_ORIGIN || "*",
      methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
      allowedHeaders: ["Content-Type", "Authorization"],
      credentials: true,
    })
  );

  // Body parsing middleware
  app.use(express.json({ limit: "10mb" }));
  app.use(express.urlencoded({ extended: true, limit: "10mb" }));

  // Rate limiting
  const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: process.env.RATE_LIMIT_MAX ? parseInt(process.env.RATE_LIMIT_MAX) : 100, // Limit each IP
    message: {
      error: "Too many requests from this IP, please try again later.",
      retryAfter: "15 minutes",
    },
    standardHeaders: true,
    legacyHeaders: false,
  });

  app.use("/api/", limiter);

  // Request logging middleware
  app.use((req: Request, res: Response, next: NextFunction) => {
    logger.info(`${req.method} ${req.path} - IP: ${req.ip}`);
    next();
  });

  // Health check endpoint (no rate limit)
  app.get("/health", (req: Request, res: Response) => {
    res.json({
      status: "ok",
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      environment: process.env.NODE_ENV || "development",
      version: "1.0.0",
    });
  });

  // Swagger documentation
  app.use("/api-docs", swaggerUi.serve, swaggerUi.setup(swaggerSpec, {
    customSiteTitle: "Yield Agent API Documentation",
    customCss: ".swagger-ui .topbar { display: none }",
    swaggerOptions: {
      persistAuthorization: true,
    },
  }));

  // API routes
  app.use("/api/v1", router);

  // Root endpoint
  app.get("/", (req: Request, res: Response) => {
    res.json({
      name: "Yield Optimization Agent API",
      version: "1.0.0",
      description: "AI-powered DeFi yield optimization service",
      documentation: "/api-docs",
      health: "/health",
      endpoints: {
        agent: "/api/v1/agent",
        tokens: "/api/v1/tokens",
        protocols: "/api/v1/protocols",
        transactions: "/api/v1/transactions",
        chains: "/api/v1/chains",
      },
    });
  });

  // 404 handler
  app.use((req: Request, res: Response) => {
    res.status(404).json({
      error: "Not Found",
      message: `Cannot ${req.method} ${req.path}`,
      documentation: "/api-docs",
    });
  });

  // Error handling middleware (must be last)
  app.use(errorHandler);

  return app;
}

/**
 * Start the API server
 */
export async function startServer(port?: number): Promise<void> {
  const app = createApp();
  const serverPort = port || parseInt(process.env.PORT || "3000");

  // Validate required environment variables
  const requiredEnvVars = ["OPENAI_API_KEY", "ENSO_API_KEY"];
  const missingEnvVars = requiredEnvVars.filter(
    (varName) => !process.env[varName]
  );

  if (missingEnvVars.length > 0) {
    logger.error(
      `Missing required environment variables: ${missingEnvVars.join(", ")}`
    );
    logger.info("Please set these in your .env file");
  }

  const server = app.listen(serverPort, () => {
    logger.info(`🚀 Yield Agent API Server running on port ${serverPort}`);
    logger.info(`📚 API Documentation: http://localhost:${serverPort}/api-docs`);
    logger.info(`💚 Health Check: http://localhost:${serverPort}/health`);
    logger.info(`🔧 Environment: ${process.env.NODE_ENV || "development"}`);
  });

  // Graceful shutdown
  process.on("SIGTERM", () => {
    logger.info("SIGTERM signal received: closing HTTP server");
    server.close(() => {
      logger.info("HTTP server closed");
      process.exit(0);
    });
  });

  process.on("SIGINT", () => {
    logger.info("SIGINT signal received: closing HTTP server");
    server.close(() => {
      logger.info("HTTP server closed");
      process.exit(0);
    });
  });
}

// Start server if run directly
// ES module equivalent of require.main === module
// Check if this module is being run directly (not imported)
const isMainModule = (() => {
  try {
    const mainModulePath = process.argv[1];
    if (!mainModulePath) return false;
    
    // Convert import.meta.url to file path for comparison
    const currentModulePath = fileURLToPath(import.meta.url);
    
    // Check if main module path ends with server.ts or server.js
    // tsx runs .ts files directly, so we check for both
    return (
      mainModulePath === currentModulePath ||
      mainModulePath.includes("server.ts") ||
      mainModulePath.includes("server.js")
    );
  } catch {
    return false;
  }
})();

if (isMainModule) {
  startServer().catch((error) => {
    logger.error("Failed to start server:", error);
    process.exit(1);
  });
}

