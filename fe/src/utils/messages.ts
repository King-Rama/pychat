import {CurrentUserInfoDto, FileModelDto, MessageModelDto, RoomDto, UserDto} from './dto';

export interface DefaultMessage {
  action: string;
  handler: string;
}

export interface SetWsIdMessage extends DefaultMessage {
  rooms:  RoomDto[];
  users: UserDto[];
  online: number[];
  opponentWsId: string;
  userInfo: CurrentUserInfoDto;
}

interface ChangeUserOnline extends DefaultMessage, UserDto {
  content: number[];
  time: number;
}

export interface DeleteRoomMessage extends DefaultMessage {
  roomId: number;
}

export interface AddOnlineUserMessage extends ChangeUserOnline {}
export interface RemoveOnlineUserMessage extends ChangeUserOnline {}

export interface AddRoomMessage extends DefaultMessage {
  roomId: number;
  users: number[];
  userId: number;
  volume: number;
  notifications: boolean;
  name: string;
  time: number;
}

export interface LeaveUserMessage extends DefaultMessage {
  roomId: number;
  userId: number;
  users: number[];
}


export interface LoadMessages extends DefaultMessage {
  content: MessageModelDto[];
  roomId: number;
}

export interface GrowlMessage extends DefaultMessage {
  content: string;
}

export interface DeleteMessage extends DefaultMessage {
  roomId: number;
  id: number;
  edited: number;
}


export interface EditMessage extends DeleteMessage {
  messageId: number;
  userId: number;
  content: string;
  time: number;
  files: Map<number, FileModelDto>;
  symbol: string;
  giphy: string;
  deleted: boolean;
}
