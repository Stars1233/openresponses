import { describe, expect, test } from "bun:test";
import { getAddedIn } from "./schema";
import type { OpenApiDocument } from "./types";

const doc: OpenApiDocument = {
  openapi: "3.1.0",
  paths: {},
  components: {
    schemas: {
      VersionedSchema: {
        type: "object",
        "x-openresponses-added-in": "2026-04-24",
      },
    },
  },
};

describe("getAddedIn", () => {
  test("reads a version directly from a schema", () => {
    expect(
      getAddedIn(doc, {
        type: "string",
        "x-openresponses-added-in": "2026-04-24",
      }),
    ).toBe("2026-04-24");
  });

  test("reads a version through a schema reference", () => {
    expect(
      getAddedIn(doc, { $ref: "#/components/schemas/VersionedSchema" }),
    ).toBe("2026-04-24");
  });

  test("returns null for unversioned schemas", () => {
    expect(getAddedIn(doc, { type: "string" })).toBeNull();
  });
});
