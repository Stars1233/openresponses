import { describe, expect, it } from "bun:test";
import { webSocketResponseCreateEventSchema } from "../generated/kubb/zod/webSocketResponseCreateEventSchema";
import { testTemplates } from "./compliance-tests";

const websocketTemplateIds = [
  "websocket-response",
  "websocket-sequential-responses",
  "websocket-continuation",
  "websocket-generate-false",
  "websocket-previous-response-not-found",
  "websocket-failed-continuation-evicts-cache",
];

describe("WebSocket compliance coverage", () => {
  it("rejects HTTP-only response create fields in WebSocket request events", () => {
    const baseRequest = {
      type: "response.create",
      model: "test-model",
      store: false,
      input: "hello",
    };

    expect(
      webSocketResponseCreateEventSchema.safeParse(baseRequest).success,
    ).toBe(true);
    expect(
      webSocketResponseCreateEventSchema.safeParse({
        ...baseRequest,
        stream: true,
      }).success,
    ).toBe(false);
    expect(
      webSocketResponseCreateEventSchema.safeParse({
        ...baseRequest,
        stream_options: { include_usage: true },
      }).success,
    ).toBe(false);
    expect(
      webSocketResponseCreateEventSchema.safeParse({
        ...baseRequest,
        background: true,
      }).success,
    ).toBe(false);
  });

  it("keeps a compliance template for each testable WebSocket requirement", () => {
    const actualIds = testTemplates.map((template) => template.id);

    for (const id of websocketTemplateIds) {
      expect(actualIds).toContain(id);
    }
  });

  it("keeps WebSocket template seed requests valid for the WebSocket schema", () => {
    const websocketTemplates = testTemplates.filter(
      (template) => template.transport === "websocket",
    );
    const config = {
      baseUrl: "https://example.com/v1",
      apiKey: "test-key",
      model: "test-model",
      runtime: "server" as const,
      authHeaderName: "Authorization",
      useBearerPrefix: true,
    };

    for (const template of websocketTemplates) {
      const result = webSocketResponseCreateEventSchema.safeParse(
        template.getRequest(config),
      );
      expect(result.success).toBe(true);
    }
  });

  it("accepts continuation request shapes used by WebSocket cache tests", () => {
    const continuationRequest = {
      type: "response.create",
      model: "test-model",
      store: false,
      previous_response_id: "resp_123",
      input: [
        {
          type: "function_call_output",
          call_id: "call_123",
          output: "tool result",
        },
      ],
    };

    expect(
      webSocketResponseCreateEventSchema.safeParse(continuationRequest).success,
    ).toBe(true);
  });
});
