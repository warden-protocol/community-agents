# Warden Agent Builder Incentive Programme

## 專案目標
為 Warden Protocol Agent Builder Incentive Programme 開發 AI agents，獲取獎勵（首月 Top 10 最高 $10,000/agent）。

## 技術要求（官方）
- 框架：僅支援 LangGraph（TypeScript 或 Python）
- 部署：LangGraph Cloud 或自架（需要 API 可存取，不需要 UI）
- 一個 LangGraph instance 只能有一個 agent
- Agent 無法存取用戶錢包、無法儲存數據在 Warden 基礎設施（2026 初解除）
- 可以連接外部 API、使用自己的資料庫

## 獎勵條件
- Clean code
- Great docs
- 創新或冷門類別有額外獎勵

## API 格式規範（重要教訓）

<rule name="array_response_format">
GET /assistants 和 POST /threads/search 必須直接回傳陣列 [{...}]，不是 {assistants: [...]}。
Why: 前端用 .map() 處理，物件包裝會導致 "t.map is not a function" 錯誤。
</rule>

<rule name="assistants_search_endpoint">
必須實作 POST /assistants/search endpoint，Warden App 依賴此 API 獲取 assistant_id。
Request: { "metadata": {}, "limit": 10, "offset": 0 }
Response: 陣列格式 [{ assistant_id, graph_id, name, ... }]
Why: 此 endpoint 容易漏掉，缺少會導致 agent 無法被發現。
</rule>

### 完整必要 endpoints 清單
| Method | Endpoint | 回傳格式 |
|--------|----------|----------|
| GET | /health | 物件 |
| GET | /info | 物件 |
| GET | /assistants | 陣列 |
| POST | /assistants/search | 陣列 |
| POST | /threads/search | 陣列 |
| POST | /threads/:id/runs/wait | 物件 |
| POST | /threads/:id/runs/stream | SSE |

## 已完成的 Agents
1. ZenGuard Agent - AI 情感守護系統，保護加密交易者避免衝動決策
   - GitHub: https://github.com/ccclin111/zenguard-agent
   - 部署: https://zenguard-agent.onrender.com
   - PR #30: https://github.com/warden-protocol/community-agents/pull/30
   - 狀態: 等待審核

2. DeFi Risk Scanner - AI 驅動的 DeFi 協議風險評估工具
   - GitHub: https://github.com/ccclin111/defi-risk-scanner
   - 部署: https://defi-risk-scanner.onrender.com
   - PR #33: https://github.com/warden-protocol/community-agents/pull/33
   - 狀態: 等待審核

## 範例 Agents（官方）
- langgraph-quick-start: 最簡單（TypeScript）
- langgraph-quick-start-py: 最簡單（Python）
- weather-agent: 推薦新手
- coingecko-agent: 較複雜
- portfolio-agent: 較複雜

## 資源
- community-agents repo: https://github.com/warden-protocol/community-agents
- 文檔: https://github.com/warden-protocol/community-agents/tree/main/docs
- Warden Discord: #developers
- Agent Chat 測試: https://agentchat.vercel.app
- Warden Studio: 即將上線（註冊和變現平台）

## 發布流程
1. 開發 agent
2. 部署到 Render 或其他平台
3. 在 Agent Chat 測試
4. Fork community-agents，加入 agents/ 目錄
5. 提交 PR
6. Warden Studio 上線後註冊
