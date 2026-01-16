/**
 * Input validation service
 * Validates all user inputs before processing
 */

import { isAddress } from 'viem';
import { ValidationResult, SUPPORTED_CHAINS, getChainById, getChainByName } from '../common/types';
import { TokenInput, QuickModeInput } from './types';
import { Logger } from '../common/logger';

const logger = new Logger('ValidationService');

/**
 * Validate token input
 * CRITICAL: If address is provided, chain MUST be provided
 */
export function validateTokenInput(input: TokenInput): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check if input is an address
  const isTokenAddress = isAddress(input.token);

  if (isTokenAddress) {
    // Address provided - chain is REQUIRED
    if (!input.chainId && !input.chainName) {
      return {
        valid: false,
        error:
          'Chain must be provided when token address is used. Please specify chainId or chainName.',
        requiredFields: ['chainId or chainName'],
        errors: [
          'Chain must be provided when token address is used. Please specify chainId or chainName.',
        ],
      };
    }

    // Validate address format
    if (!isAddress(input.token)) {
      errors.push('Invalid Ethereum address format');
    }

    // Validate chain if provided
    if (input.chainId) {
      const chain = getChainById(input.chainId);
      if (!chain) {
        errors.push(
          `Chain ID ${input.chainId} is not supported. Supported chains: ${SUPPORTED_CHAINS.map((c) => c.name).join(', ')}`,
        );
      }
    } else if (input.chainName) {
      const chain = getChainByName(input.chainName);
      if (!chain) {
        errors.push(
          `Chain "${input.chainName}" is not supported. Supported chains: ${SUPPORTED_CHAINS.map((c) => c.name).join(', ')}`,
        );
      }
    }
  }

  // Validate token is not empty
  if (!input.token || input.token.trim().length === 0) {
    errors.push('Token name or address cannot be empty');
  }

  return {
    valid: errors.length === 0,
    errors: errors.length > 0 ? errors : undefined,
    warnings: warnings.length > 0 ? warnings : undefined,
  };
}

/**
 * Validate chain
 */
export function validateChain(chain: string | number): ValidationResult {
  const chainId = typeof chain === 'string' ? getChainByName(chain)?.id : chain;

  if (!chainId) {
    return {
      valid: false,
      error: `Unsupported chain: ${chain}`,
      supportedChains: SUPPORTED_CHAINS.map((c) => ({
        id: c.id,
        name: c.name,
      })),
    };
  }

  const chainInfo = getChainById(chainId);
  if (!chainInfo) {
    return {
      valid: false,
      error: `Chain ID ${chainId} is not supported`,
      supportedChains: SUPPORTED_CHAINS.map((c) => ({
        id: c.id,
        name: c.name,
      })),
    };
  }

  return { valid: true, data: chainInfo };
}

/**
 * Validate amount
 */
export function validateAmount(
  amount: string,
  balance: bigint,
  decimals: number,
): ValidationResult {
  const amountNum = parseFloat(amount);

  if (isNaN(amountNum) || amountNum <= 0) {
    return {
      valid: false,
      error: 'Amount must be a positive number',
    };
  }

  // Convert amount to wei for comparison
  const amountWei = BigInt(Math.floor(amountNum * Math.pow(10, decimals)));

  if (amountWei > balance) {
    const balanceFormatted = Number(balance) / Math.pow(10, decimals);
    return {
      valid: false,
      error: `Insufficient balance. Available: ${balanceFormatted}, Requested: ${amount}`,
      data: {
        available: balanceFormatted.toString(),
        requested: amount,
      },
    };
  }

  return { valid: true, data: { amountWei, amountNum } };
}

/**
 * Detect if input is quick mode (has protocol specified)
 */
export function detectQuickMode(input: string): boolean {
  // Simple heuristic: if input contains protocol keywords or structure suggests quick mode
  const quickModeKeywords = ['to', 'on', 'deposit', 'stake', 'protocol'];
  const lowerInput = input.toLowerCase();

  // Check if input has structure like "token on chain to protocol"
  const hasProtocolStructure =
    lowerInput.includes(' to ') ||
    (lowerInput.includes(' on ') && lowerInput.length > 20);

  return hasProtocolStructure || quickModeKeywords.some((keyword) => lowerInput.includes(keyword));
}

/**
 * Parse quick mode input
 * This is a simplified parser - in production, you might want to use LLM for better parsing
 */
export function parseQuickModeInput(input: string): QuickModeInput | Error {
  try {
    // This is a basic parser - can be enhanced with LLM or more sophisticated parsing

    // Try to extract amount (number at the start or after "deposit")
    let amount: string | undefined;
    const amountMatch = input.match(/(?:deposit|stake)\s+(\d+(?:\.\d+)?)/i);
    if (amountMatch) {
      amount = amountMatch[1];
    }

    // Try to extract chain (common chain names)
    const chainPatterns = [
      /(?:on|chain)\s+(ethereum|arbitrum|optimism|polygon|base|avalanche|bnb|binance)/i,
      /(?:on|chain)\s+(\d+)/,
    ];
    let chain: string | number | undefined;
    for (const pattern of chainPatterns) {
      const match = input.match(pattern);
      if (match) {
        chain = isNaN(Number(match[1])) ? match[1] : Number(match[1]);
        break;
      }
    }

    // Try to extract protocol (after "to" or common protocol names)
    const protocolMatch = input.match(/(?:to|protocol)\s+([a-z0-9-]+)/i);
    const protocol = protocolMatch ? protocolMatch[1] : undefined;

    // Try to extract token (address or name)
    const addressMatch = input.match(/0x[a-fA-F0-9]{40}/);
    const token = addressMatch
      ? addressMatch[0]
      : input.split(/\s+(?:on|to|deposit|stake)/i)[0]?.trim() || '';

    if (!token) {
      return new Error('Could not extract token from input');
    }

    return {
      token,
      chain: chain || '',
      protocol: protocol || '',
      amount,
    };
  } catch (error) {
    return error instanceof Error ? error : new Error('Failed to parse quick mode input');
  }
}

/**
 * Validate quick mode input
 */
export function validateQuickModeInput(input: QuickModeInput): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Validate token
  if (isAddress(input.token)) {
    if (!input.chain) {
      errors.push('Chain is required when using token address');
    }
    if (!isAddress(input.token)) {
      errors.push('Invalid token address format');
    }
  }

  // Validate chain
  if (input.chain) {
    const chainValidation = validateChain(input.chain);
    if (!chainValidation.valid) {
      errors.push(chainValidation.error || 'Invalid chain');
    }
  } else {
    errors.push('Chain must be specified in quick mode');
  }

  // Validate protocol
  if (!input.protocol || input.protocol.trim().length === 0) {
    errors.push('Protocol must be specified in quick mode');
  }

  // Validate amount if provided
  if (input.amount) {
    const amountNum = parseFloat(input.amount);
    if (isNaN(amountNum) || amountNum <= 0) {
      errors.push('Invalid amount. Must be a positive number');
    }
  }

  return {
    valid: errors.length === 0,
    errors: errors.length > 0 ? errors : undefined,
    warnings: warnings.length > 0 ? warnings : undefined,
    data: errors.length === 0 ? input : undefined,
  };
}

/**
 * Comprehensive input validation
 */
export function validateInput(input: string): ValidationResult {
  // Check if it's quick mode
  const isQuickMode = detectQuickMode(input);

  if (isQuickMode) {
    logger.info('Detected quick mode input');
    const parsed = parseQuickModeInput(input);

    if (parsed instanceof Error) {
      return {
        valid: false,
        error: parsed.message,
        errors: [parsed.message],
      };
    }

    return validateQuickModeInput(parsed);
  }

  // Regular mode - basic validation
  if (!input || input.trim().length === 0) {
    return {
      valid: false,
      error: 'Input cannot be empty',
      errors: ['Input cannot be empty'],
    };
  }

  return {
    valid: true,
    data: { input, mode: 'interactive' },
  };
}

