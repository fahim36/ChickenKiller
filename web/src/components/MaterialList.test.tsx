import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { MaterialList } from "./MaterialList";

afterEach(cleanup);

it("links each Material and labels its type", () => {
  render(
    <MaterialList
      materials={[
        { id: "mcp-spec", title: "MCP spec", url: "https://modelcontextprotocol.io", type: "docs" },
        { id: "cs336", title: "CS336", url: "https://example.com/cs336", type: "video" },
      ]}
    />,
  );
  const link = screen.getByRole("link", { name: "MCP spec" });
  expect(link.getAttribute("href")).toBe("https://modelcontextprotocol.io");
  expect(link.getAttribute("target")).toBe("_blank");
  expect(screen.getByText("Official docs")).toBeTruthy();
  expect(screen.getByText("Video")).toBeTruthy();
});

it("says so when a Lesson has no Materials", () => {
  render(<MaterialList materials={[]} />);
  expect(screen.getByText("No Materials for this Lesson.")).toBeTruthy();
});
