import { register } from "node:module";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

// we only care about the payload, which contains the server definition
const graphs = JSON.parse(process.env.LANGSERVE_GRAPHS || "{}");
const cwd = process.cwd();

// find the first file, as `parentURL` needs to be a valid file URL
// if no graph found, just assume a dummy default file, which should
// be working fine as well.
const firstGraphFile =
  Object.values(graphs)
    .map((i) => {
      if (typeof i === "string") {
        return i.split(":").at(0);
      } else if (i && typeof i === "object" && i.path) {
        return i.path.split(":").at(0);
      }
      return null;
    })
    .filter(Boolean)
    .at(0) || "index.mts";

// enforce API @langchain/langgraph resolution
register("./load.hooks.mjs", import.meta.url, {
  parentURL: "data:",
  data: { parentURL: pathToFileURL(join(cwd, firstGraphFile)).toString() },
});
