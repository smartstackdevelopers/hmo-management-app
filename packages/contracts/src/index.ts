export type ServiceName = "hmore-web" | "hmore-api" | "hmore-ai";

export interface HealthResponse {
  status: "ok";
  service: ServiceName;
  version: string;
}

export interface ApiHealthDetails extends HealthResponse {
  api: "v1";
}
