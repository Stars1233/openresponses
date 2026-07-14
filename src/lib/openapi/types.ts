export type OpenApiDocument = {
  openapi: string;
  info?: {
    title?: string;
    version?: string;
  };
  servers?: Array<{ url: string }>;
  paths: Record<string, OpenApiPathItem>;
  components?: {
    schemas?: Record<string, OpenApiSchema>;
    parameters?: Record<string, OpenApiParameter>;
    responses?: Record<string, OpenApiResponse>;
    requestBodies?: Record<string, OpenApiRequestBody>;
  };
};

export type OpenApiPathItem = {
  "x-openresponses-added-in"?: string;
  "x-openresponses-websocket"?: {
    "x-openresponses-added-in"?: string;
    [key: string]: unknown;
  };
  get?: OpenApiOperation;
  put?: OpenApiOperation;
  post?: OpenApiOperation;
  delete?: OpenApiOperation;
  patch?: OpenApiOperation;
  options?: OpenApiOperation;
  head?: OpenApiOperation;
  trace?: OpenApiOperation;
  parameters?: Array<OpenApiParameter | OpenApiReference>;
};

export type OpenApiOperation = {
  "x-openresponses-added-in"?: string;
  operationId?: string;
  summary?: string;
  description?: string;
  deprecated?: boolean;
  parameters?: Array<OpenApiParameter | OpenApiReference>;
  requestBody?: OpenApiRequestBody | OpenApiReference;
  responses?: Record<string, OpenApiResponse | OpenApiReference>;
};

export type OpenApiReference = { $ref: string };

export type OpenApiSchema = {
  // NOTE: In OpenAPI 3.1, schemas are full JSON Schema vocab; we keep this loose.
  $ref?: string;
  title?: string;
  description?: string;
  type?: string;
  format?: string;
  enum?: unknown[];
  const?: unknown;
  default?: unknown;
  example?: unknown;
  examples?: unknown[];
  deprecated?: boolean;
  "x-openresponses-added-in"?: string;

  properties?: Record<string, OpenApiSchema>;
  required?: string[];
  items?: OpenApiSchema;
  additionalProperties?: boolean | OpenApiSchema;

  oneOf?: OpenApiSchema[];
  anyOf?: OpenApiSchema[];
  allOf?: OpenApiSchema[];

  discriminator?: {
    propertyName: string;
    mapping?: Record<string, string>;
  };
};

export type OpenApiMediaTypeObject = {
  schema?: OpenApiSchema;
  example?: unknown;
  examples?: Record<
    string,
    { value?: unknown; summary?: string; description?: string }
  >;
};

export type OpenApiRequestBody = {
  $ref?: string;
  description?: string;
  required?: boolean;
  content?: Record<string, OpenApiMediaTypeObject>;
};

export type OpenApiParameter = {
  $ref?: string;
  name: string;
  in: "query" | "header" | "path" | "cookie";
  required?: boolean;
  deprecated?: boolean;
  description?: string;
  schema?: OpenApiSchema;
};

export type OpenApiResponse = {
  $ref?: string;
  description?: string;
  headers?: Record<string, OpenApiParameter | OpenApiReference>;
  content?: Record<string, OpenApiMediaTypeObject>;
};
