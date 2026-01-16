/**
 * ZenGuard Risk Engine
 * Calculates 'Irrationality Index' to decide if Warden Protocol protection is needed.
 */
export function calculateIrrationalityIndex(
  sentimentScore: number,     // -1 (Fear) to 1 (Greed)
  sentimentIntensity: number, // 0 to 1
  marketVolatility: number    // 0 to 1 (Congestion/Volatility)
): number {

  // 1. Sentiment Deviation
  const sentimentDeviation = Math.abs(sentimentScore) * sentimentIntensity;

  // 2. Dynamic Weights
  let w_sentiment = 0.4;
  let w_volatility = 0.3;
  let w_baseline = 0.3;

  if (marketVolatility > 0.7) {
    w_sentiment += 0.2;
    w_volatility -= 0.1;
    w_baseline -= 0.1;
  }

  // 3. Weighted Score
  let rawScore =
    (w_sentiment * sentimentDeviation) +
    (w_volatility * marketVolatility) +
    (w_baseline * 0.2);

  // 4. Smart Demo Boost
  // Only apply boost if we detect actual negative/emotional sentiment (>0.1 deviation)
  // This prevents locking on neutral queries like "Hello"
  if (sentimentDeviation > 0.1) {
     console.log("  [DEBUG] Emotional variance detected. Applying Demo Boost (+0.2)...");
     rawScore += 0.2;
  }

  // 5. Sigmoid Activation
  const riskScore = 1 / (1 + Math.exp(-10 * (rawScore - 0.5)));

  return parseFloat(riskScore.toFixed(2));
}

export function determineIntervention(riskScore: number): "NONE" | "WARNING" | "HARD_LOCK" {
  if (riskScore > 0.8) return "HARD_LOCK";
  if (riskScore > 0.5) return "WARNING";
  return "NONE";
}
