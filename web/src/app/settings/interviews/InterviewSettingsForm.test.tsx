import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { InterviewSettingsForm } from "./InterviewSettingsForm";
import { updateInterviewSettings } from "./actions";
vi.mock("./actions", () => ({ updateInterviewSettings: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
it("discloses attestation and processing before explicit enablement", async () => {
  const initial = {
    enabled: false,
    processing_consent: false,
    free_project_confirmed: false,
  };
  vi.mocked(updateInterviewSettings).mockResolvedValue({
    enabled: true,
    processing_consent: true,
    free_project_confirmed: true,
  });
  render(<InterviewSettingsForm initial={initial} />);
  expect(screen.getByText(/cannot verify billing/)).toBeTruthy();
  expect(screen.getByText(/product-improvement use/)).toBeTruthy();
  for (const checkbox of screen.getAllByRole("checkbox"))
    fireEvent.click(checkbox);
  fireEvent.click(
    screen.getByRole("button", { name: "Save interview settings" }),
  );
  await screen.findByRole("status");
  expect(updateInterviewSettings).toHaveBeenCalledWith({
    enabled: true,
    processing_consent: true,
    free_project_confirmed: true,
  });
});
