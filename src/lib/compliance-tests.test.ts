import { describe, expect, it } from "bun:test";
import { webSocketErrorEventSchema } from "../generated/kubb/zod/webSocketErrorEventSchema";
import { webSocketResponseCreateEventSchema } from "../generated/kubb/zod/webSocketResponseCreateEventSchema";
import { testTemplates } from "./compliance-tests";
import { parseStreamingEventData } from "./sse-parser";

const websocketTemplateIds = [
  "websocket-response",
  "websocket-sequential-responses",
  "websocket-continuation",
  "websocket-reconnect-store-false-recovery",
  "websocket-previous-response-not-found",
  "websocket-failed-continuation-evicts-cache",
  "websocket-compact-new-chain",
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

  it("accepts documented WebSocket error envelopes", () => {
    const previousResponseNotFound = {
      type: "error",
      status: 400,
      error: {
        code: "previous_response_not_found",
        message: "Previous response with id 'resp_abc' not found.",
        param: "previous_response_id",
      },
    };
    const connectionLimitReached = {
      type: "error",
      error: {
        type: "invalid_request_error",
        code: "websocket_connection_limit_reached",
        message:
          "Responses websocket connection limit reached (60 minutes). Create a new websocket connection to continue.",
      },
      status: 400,
    };

    expect(
      webSocketErrorEventSchema.safeParse(previousResponseNotFound).success,
    ).toBe(true);
    expect(
      webSocketErrorEventSchema.safeParse(connectionLimitReached).success,
    ).toBe(true);
    expect(
      parseStreamingEventData(previousResponseNotFound, undefined, {
        transport: "websocket",
      }).validationResult.success,
    ).toBe(true);
    expect(
      parseStreamingEventData(connectionLimitReached, undefined, {
        transport: "websocket",
      }).validationResult.success,
    ).toBe(true);
  });
});
