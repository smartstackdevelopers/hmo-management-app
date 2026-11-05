import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({
    status: "ok",
    service: "hmore-web",
    version: "0.1.0",
  });
}
