import type { ChatRoom } from "../types";

export interface RoomListProps {
  rooms: ChatRoom[];
  selectedRoomId: string | null;
  onSelectRoom: (roomId: string) => void;
}

function statusLabel(status: ChatRoom["status"]): string {
  return status === "active" ? "진행 중" : "완료";
}

function formatCreatedAt(createdAt: string): string {
  const date = new Date(createdAt);
  return Number.isNaN(date.getTime()) ? createdAt : date.toLocaleDateString();
}

export function RoomList({
  rooms,
  selectedRoomId,
  onSelectRoom,
}: RoomListProps) {
  if (rooms.length === 0) {
    return (
      <nav aria-label="채팅방 목록" className="room-list">
        <p className="room-list__empty">채팅방이 없습니다.</p>
      </nav>
    );
  }

  return (
    <nav aria-label="채팅방 목록" className="room-list">
      <ul className="room-list__items">
        {rooms.map((room) => {
          const isSelected = room.id === selectedRoomId;
          const className = [
            "room",
            `room--${room.status}`,
            isSelected ? "room--selected" : "",
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <li key={room.id}>
              <button
                type="button"
                className={className}
                aria-current={isSelected ? "true" : undefined}
                onClick={() => onSelectRoom(room.id)}
              >
                <span className="room__title">주간보고</span>
                <span className="room__date">
                  {formatCreatedAt(room.createdAt)}
                </span>
                <span className={`room__status room__status--${room.status}`}>
                  {statusLabel(room.status)}
                </span>
                <span className="room__id">{room.id}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
