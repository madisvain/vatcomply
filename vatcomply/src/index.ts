import { Hono } from "hono";

const app = new Hono();

app.get("/rates", (c) => {
  return c.json({});
});

export default app;
