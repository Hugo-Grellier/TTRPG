// Unpack a Foundry LevelDB compendium pack into one JSON file per document.
// Usage: node unpack.mjs <pack-dir> <out-dir>
import { extractPack } from "@foundryvtt/foundryvtt-cli";

const [pack, out] = process.argv.slice(2);
await extractPack(pack, out, { log: false });
