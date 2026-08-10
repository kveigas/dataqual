import { expect, test, vi } from "vitest";

import { api } from "./api";

test("rejects a response that violates the API contract", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([{ dataset_id: 42 }]), { status: 200 }));
  await expect(api.datasets()).rejects.toThrow();
});

test("uses the server error message", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: { message: "invalid source" } }), { status: 422 }));
  await expect(api.datasets()).rejects.toThrow("invalid source");
});
