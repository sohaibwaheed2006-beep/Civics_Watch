export type NotificationType =
  | 'status_change'
  | 'assignment'
  | 'comment'
  | 'resolution'
  | 'system';

export interface Notification {
  id: string;
  userId: string;
  title: string;
  message: string;
  type: NotificationType;
  reportId?: string;
  isRead: boolean;
  createdAt: string;
}
