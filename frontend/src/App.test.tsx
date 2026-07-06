import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

// Smoke test verifying the Frontend scaffold renders. Feature tests are added
// by the [FE] track tasks.
describe("App scaffold", () => {
  it("renders the app heading", () => {
    render(<App />);
    expect(
      screen.getByRole("heading", { name: "주간보고 채팅" }),
    ).toBeInTheDocument();
  });
});
