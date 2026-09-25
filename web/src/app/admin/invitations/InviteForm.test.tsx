import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { InviteForm, type InviteState } from "./InviteForm";

afterEach(cleanup);

it("sends the typed email address and shows the result", async () => {
  const action = vi.fn(
    async (_: InviteState, form: FormData): Promise<InviteState> => ({
      ok: true,
      message: `Invited ${form.get("email")}.`,
    }),
  );
  render(<InviteForm action={action} />);

  fireEvent.change(screen.getByRole("textbox", { name: "Email address" }), {
    target: { value: "ada@example.com" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Invite" }));

  expect((await screen.findByRole("status")).textContent).toBe("Invited ada@example.com.");
});
