import React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import * as Tabs from "@radix-ui/react-tabs";
import { QueryClient } from "@tanstack/react-query";
import { ResponsiveContainer } from "recharts";
import { z } from "zod";

const checks = {
  react: typeof React.createElement === "function",
  radixDialog: typeof Dialog.Root !== "undefined",
  radixTabs: typeof Tabs.Root !== "undefined",
  tanstackQuery: new QueryClient() instanceof QueryClient,
  recharts: typeof ResponsiveContainer !== "undefined",
  zod: z.object({ ok: z.boolean() }).parse({ ok: true }).ok,
};

if (Object.values(checks).some((value) => !value)) {
  throw new Error(JSON.stringify(checks));
}
console.log(JSON.stringify({ status: "pass", checks }, null, 2));
