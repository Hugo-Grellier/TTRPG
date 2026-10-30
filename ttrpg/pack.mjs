// Compile JSON documents (one file per entry, with _key fields) into a Foundry LevelDB pack.
// Usage: node pack.mjs <source-dir> <pack-dir>
import { compilePack } from "@foundryvtt/foundryvtt-cli";

const [source, pack] = process.argv.slice(2);
await compilePack(source, pack, { log: false });
