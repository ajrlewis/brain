import "server-only";
import { z } from "zod";
import {
  PageInventoryItem,
  PageResponse,
  SearchResponse,
  SkillInventoryItem,
  SourceInventoryItem,
} from "./generated/api";
import { env } from "./env";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  init: RequestInit = {},
): Promise<T> {
  const config = env();
  let response: Response;
  try {
    response = await fetch(`${config.BRAIN_API_URL}${path}`, {
      ...init,
      headers: {
        ...init.headers,
        Authorization: `Bearer ${config.LOCAL_BEARER_TOKEN}`,
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(503, "Brain API is unavailable.");
  }
  if (!response.ok)
    throw new ApiError(
      response.status,
      response.status === 403
        ? "You do not have access to this knowledge."
        : response.status === 404
          ? "This page could not be found."
          : "Brain API returned an unexpected response.",
    );
  const parsed = schema.safeParse(await response.json());
  if (!parsed.success)
    throw new ApiError(502, "Brain API returned an invalid response.");
  return parsed.data;
}
export type PageSummary = z.infer<typeof PageInventoryItem>;
export type PageDetail = z.infer<typeof PageResponse>;
export const getPages = () => request("/pages", z.array(PageInventoryItem));
export const getPage = (id: string) =>
  request(`/pages/${encodeURIComponent(id)}`, PageResponse);
export const getSkills = () => request("/skills", z.array(SkillInventoryItem));
export const getSources = () =>
  request("/sources", z.array(SourceInventoryItem));
export type SearchResults = z.infer<typeof SearchResponse>;
export const searchPages = (query: string) =>
  request("/search", SearchResponse, {
    method: "POST",
    body: JSON.stringify({ query, limit: 20 }),
    headers: { "Content-Type": "application/json" },
  });
