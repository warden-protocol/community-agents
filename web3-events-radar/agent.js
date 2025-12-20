import fetch from "node-fetch";

async function getProtocolEvents() {
  const res = await fetch("https://api.llama.fi/protocols");
  const data = await res.json();
  return data.slice(0, 3).map(p => `- ${p.name}: TVL $${Math.round(p.tvl)}M`);
}

async function getGovernanceVotes() {
  const res = await fetch("https://hub.snapshot.org/graphql", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: `
        query {
          proposals(first: 3, where: { state: "active" }) {
            title
            space { name }
          }
        }
      `
    })
  });
  const json = await res.json();
  return json.data.proposals.map(
    p => `- ${p.space.name}: ${p.title}`
  );
}

async function getFundingEvents() {
  const res = await fetch("https://api.cryptorank.io/v1/funding-rounds");
  const json = await res.json();
  return (json.data || []).slice(0, 3).map(
    f => `- ${f.projectName}: ${f.round} round`
  );
}

async function getTokenSales() {
  const res = await fetch("https://api.cryptorank.io/v1/ico-calendar");
  const json = await res.json();
  return (json.data || []).slice(0, 3).map(
    t => `- ${t.projectName}: ${t.stage}`
  );
}

export async function runAgent() {
  const protocolEvents = await getProtocolEvents();
  const governance = await getGovernanceVotes();
  const funding = await getFundingEvents();
  const tokenSales = await getTokenSales();

  return `
Web3 Events Radar — Daily Brief

Protocol & On-chain Events
${protocolEvents.join("\n")}

Governance Votes
${governance.join("\n")}

Funding & VC Activity
${funding.join("\n")}

Token Sales (Informational)
${tokenSales.join("\n")}

Educational information only. Not financial advice.
`;
}

