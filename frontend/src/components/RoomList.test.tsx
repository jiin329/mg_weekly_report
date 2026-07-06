import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RoomList } from "./RoomList";
import type { ChatRoom } from "../types";

// Helpers to build rooms without repeating the full shape everywhere.
function activeRoom(id: string, createdAt: string): ChatRoom {
  return { id, status: "active", createdAt, closedAt: null, report: null };
}

function closedRoom(id: string, createdAt: string): ChatRoom {
  return {
    id,
    status: "closed",
    createdAt,
    closedAt: createdAt,
    report: {
      writtenDate: createdAt,
      achievements: "a",
      nextWeekPlan: "p",
      issues: "i",
    },
  };
}

describe("RoomList", () => {
  it("renders both active and closed rooms (Req 7.1)", () => {
    const rooms = [
      activeRoom("r-active", "2024-03-11T09:00:00Z"),
      closedRoom("r-closed", "2024-03-04T09:00:00Z"),
    ];
    render(
      <RoomList rooms={rooms} selectedRoomId={null} onSelectRoom={() => {}} />,
    );
    // Two clickable rooms are shown.
    expect(screen.getAllByRole("button")).toHaveLength(2);
  });

  it("visually distinguishes active from closed rooms (Req 7.2)", () => {
    const rooms = [
      activeRoom("r-active", "2024-03-11T09:00:00Z"),
      closedRoom("r-closed", "2024-03-04T09:00:00Z"),
    ];
    render(
      <RoomList rooms={rooms} selectedRoomId={null} onSelectRoom={() => {}} />,
    );
    const active = screen.getByRole("button", { name: /r-active/ });
    const closed = screen.getByRole("button", { name: /r-closed/ });
    // Distinct status classes so styling/labels can differentiate them.
    expect(active.className).toContain("room--active");
    expect(closed.className).toContain("room--closed");
    // A visible status label is present for each.
    expect(active).toHaveTextContent("진행 중");
    expect(closed).toHaveTextContent("완료");
  });

  it("calls onSelectRoom with the room id when clicked (Req 7.3)", async () => {
    const user = userEvent.setup();
    const onSelectRoom = vi.fn();
    const rooms = [activeRoom("r-active", "2024-03-11T09:00:00Z")];
    render(
      <RoomList
        rooms={rooms}
        selectedRoomId={null}
        onSelectRoom={onSelectRoom}
      />,
    );
    await user.click(screen.getByRole("button", { name: /r-active/ }));
    expect(onSelectRoom).toHaveBeenCalledWith("r-active");
  });

  it("marks the selected room (Req 7.4)", () => {
    const rooms = [
      activeRoom("r-active", "2024-03-11T09:00:00Z"),
      closedRoom("r-closed", "2024-03-04T09:00:00Z"),
    ];
    render(
      <RoomList
        rooms={rooms}
        selectedRoomId="r-active"
        onSelectRoom={() => {}}
      />,
    );
    const active = screen.getByRole("button", { name: /r-active/ });
    expect(active).toHaveAttribute("aria-current", "true");
    expect(active.className).toContain("room--selected");
  });

  it("renders an empty state when there are no rooms", () => {
    render(
      <RoomList rooms={[]} selectedRoomId={null} onSelectRoom={() => {}} />,
    );
    expect(screen.queryAllByRole("button")).toHaveLength(0);
    expect(screen.getByText("채팅방이 없습니다.")).toBeInTheDocument();
  });
});
