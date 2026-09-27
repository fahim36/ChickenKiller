import { cleanup, render } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { Inline } from "./Inline";

afterEach(cleanup);

it("turns backtick spans into code", () => {
  const { container } = render(<Inline text="`is` vs `==`; interning" />);
  expect([...container.querySelectorAll("code")].map((c) => c.textContent)).toEqual(["is", "=="]);
  expect(container.textContent).toBe("is vs ==; interning");
});

it("leaves a lone backtick alone", () => {
  const { container } = render(<Inline text="a ` b" />);
  expect(container.querySelector("code")).toBeNull();
  expect(container.textContent).toBe("a ` b");
});
