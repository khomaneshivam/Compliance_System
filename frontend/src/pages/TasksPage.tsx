import React, { useState, useEffect, useCallback } from 'react';
import {
  CheckSquare,
  Search,
  Plus,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Lock,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  Paperclip,
  Calendar,
  List,
  X,
  RefreshCw,
  Send,
} from 'lucide-react';
import { api } from '../services/api';
import type { TaskItem, PaginatedTasks } from '../types';

export const TasksPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [tasksData, setTasksData] = useState<PaginatedTasks | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'calendar'>('list');
  const [calendarMonth, setCalendarMonth] = useState<Date>(new Date(2025, 9, 1)); // Oct 2025 baseline

  // Filters & Pagination
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [search, setSearch] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);
  const [sortBy, setSortBy] = useState<string>('due_date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Selected Task Detail Drawer
  const [selectedTask, setSelectedTask] = useState<TaskItem | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [newComment, setNewComment] = useState<string>('');
  const [commentSubmitting, setCommentSubmitting] = useState<boolean>(false);

  // Transition & Blocked Modal
  const [showBlockModal, setShowBlockModal] = useState<boolean>(false);
  const [blockedReason, setBlockedReason] = useState<string>('');
  const [transitioning, setTransitioning] = useState<boolean>(false);

  // Create Task Modal
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [createTitle, setCreateTitle] = useState<string>('');
  const [createDesc, setCreateDesc] = useState<string>('');
  const [createDueDate, setCreateDueDate] = useState<string>('');
  const [createPriority, setCreatePriority] = useState<'HIGH' | 'MEDIUM' | 'LOW'>('MEDIUM');
  const [createSubmitting, setCreateSubmitting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getTasks({
        status: statusFilter,
        priority: priorityFilter,
        search: search.trim() || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        page_size: pageSize,
      });
      setTasksData(data);
    } catch (err: unknown) {
      console.error('Failed to load tasks', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, priorityFilter, search, sortBy, sortOrder, page, pageSize]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleOpenDetail = async (task: TaskItem) => {
    setDetailLoading(true);
    setSelectedTask(task);
    try {
      const full = await api.getTaskDetail(task.id);
      setSelectedTask(full);
    } catch (err: unknown) {
      console.error('Failed to fetch task details', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleStatusTransition = async (newStatus: 'TODO' | 'IN_PROGRESS' | 'BLOCKED' | 'COMPLETED', comment?: string) => {
    if (!selectedTask) return;
    setTransitioning(true);
    try {
      const updated = await api.transitionTaskStatus(selectedTask.id, {
        new_status: newStatus,
        comment,
      });
      setSelectedTask((prev) => (prev ? { ...prev, ...updated, status: newStatus } : null));
      setFeedback(`Task status updated to ${newStatus}.`);
      setTimeout(() => setFeedback(null), 3000);
      setShowBlockModal(false);
      setBlockedReason('');
      fetchTasks();
    } catch (err: unknown) {
      alert((err as Error).message || 'Failed to update task status');
    } finally {
      setTransitioning(false);
    }
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask || !newComment.trim()) return;
    setCommentSubmitting(true);
    try {
      const commentObj = await api.addTaskComment(selectedTask.id, newComment.trim());
      setSelectedTask((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          comments: [...(prev.comments || []), commentObj],
          comments_count: (prev.comments_count || 0) + 1,
        };
      });
      setNewComment('');
    } catch (err: unknown) {
      alert((err as Error).message || 'Failed to add comment');
    } finally {
      setCommentSubmitting(false);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createTitle || !createDueDate) return;
    setCreateSubmitting(true);
    try {
      await api.createTask({
        plant_id: 'plant-default',
        title: createTitle,
        description: createDesc,
        due_date: createDueDate,
        priority: createPriority,
      });
      setShowCreateModal(false);
      setCreateTitle('');
      setCreateDesc('');
      setCreateDueDate('');
      setFeedback('Remediation task created successfully.');
      setTimeout(() => setFeedback(null), 3000);
      fetchTasks();
    } catch (err: unknown) {
      alert((err as Error).message || 'Failed to create task');
    } finally {
      setCreateSubmitting(false);
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'TODO':
        return <span className="badge badge-neutral"><Clock size={12} /> To Do</span>;
      case 'IN_PROGRESS':
        return <span className="badge badge-info"><RefreshCw size={12} className="spin" /> In Progress</span>;
      case 'BLOCKED':
        return <span className="badge badge-critical"><Lock size={12} /> Blocked</span>;
      case 'COMPLETED':
        return <span className="badge badge-success"><CheckCircle2 size={12} /> Completed</span>;
      default:
        return <span className="badge badge-neutral">{status}</span>;
    }
  };

  const renderPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'HIGH':
        return <span className="badge badge-critical">High Priority</span>;
      case 'MEDIUM':
        return <span className="badge badge-warning">Medium Priority</span>;
      case 'LOW':
        return <span className="badge badge-neutral">Low Priority</span>;
      default:
        return <span className="badge badge-neutral">{priority}</span>;
    }
  };

  return (
    <div className="tasks-page" style={{ padding: '24px 32px' }}>
      {/* Toast Feedback */}
      {feedback && (
        <div className="banner banner-success" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={16} />
          <span>{feedback}</span>
        </div>
      )}

      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
        <div>
          <h1 style={{ fontSize: '24px', fontWeight: 600, color: '#0f172a', margin: '0 0 4px 0' }}>
            Remediation & Compliance Tasks
          </h1>
          <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
            Operational task board tracking corrective actions, audit findings, evidence renewals, and equipment servicing.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{ display: 'inline-flex', background: '#e2e8f0', borderRadius: '6px', padding: '2px' }}>
            <button
              onClick={() => setViewMode('list')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                border: 'none',
                borderRadius: '4px',
                fontSize: '12.5px',
                fontWeight: 600,
                cursor: 'pointer',
                background: viewMode === 'list' ? '#ffffff' : 'transparent',
                color: viewMode === 'list' ? '#0f172a' : '#64748b',
                boxShadow: viewMode === 'list' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              }}
            >
              <List size={14} /> List View
            </button>
            <button
              onClick={() => setViewMode('calendar')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                border: 'none',
                borderRadius: '4px',
                fontSize: '12.5px',
                fontWeight: 600,
                cursor: 'pointer',
                background: viewMode === 'calendar' ? '#ffffff' : 'transparent',
                color: viewMode === 'calendar' ? '#0f172a' : '#64748b',
                boxShadow: viewMode === 'calendar' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              }}
            >
              <Calendar size={14} /> Calendar View
            </button>
          </div>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            <Plus size={14} /> New Remediation Task
          </button>
        </div>
      </div>

      {/* Status Filter Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px' }}>
        {[
          { id: 'ALL', label: 'All Tasks' },
          { id: 'TODO', label: 'To Do' },
          { id: 'IN_PROGRESS', label: 'In Progress' },
          { id: 'BLOCKED', label: 'Blocked' },
          { id: 'COMPLETED', label: 'Resolved' },
        ].map((tab) => {
          const isActive = statusFilter === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setStatusFilter(tab.id);
                setPage(1);
              }}
              style={{
                background: isActive ? '#06281e' : '#ffffff',
                color: isActive ? '#ffffff' : '#475569',
                border: '1px solid',
                borderColor: isActive ? '#06281e' : '#cbd5e1',
                padding: '6px 14px',
                borderRadius: '6px',
                fontSize: '13px',
                fontWeight: isActive ? 600 : 500,
                cursor: 'pointer',
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Search and Secondary Filter Controls */}
      <div
        style={{
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          padding: '14px 16px',
          marginBottom: '20px',
          display: 'grid',
          gridTemplateColumns: '2fr 1fr 1fr auto',
          gap: '12px',
          alignItems: 'center',
        }}
      >
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: '#94a3b8' }} />
          <input
            type="text"
            className="input-field"
            placeholder="Search tasks by title, code or description..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            style={{ paddingLeft: '32px', width: '100%', fontSize: '13px' }}
          />
        </div>
        <div>
          <select
            className="input-field"
            value={priorityFilter}
            onChange={(e) => {
              setPriorityFilter(e.target.value);
              setPage(1);
            }}
            style={{ width: '100%', fontSize: '13px' }}
          >
            <option value="ALL">All Priorities</option>
            <option value="HIGH">High Priority</option>
            <option value="MEDIUM">Medium Priority</option>
            <option value="LOW">Low Priority</option>
          </select>
        </div>
        <div>
          <select
            className="input-field"
            value={`${sortBy}:${sortOrder}`}
            onChange={(e) => {
              const [sb, so] = e.target.value.split(':');
              setSortBy(sb);
              setSortOrder(so as 'asc' | 'desc');
            }}
            style={{ width: '100%', fontSize: '13px' }}
          >
            <option value="due_date:asc">Due Date (Earliest First)</option>
            <option value="due_date:desc">Due Date (Latest First)</option>
            <option value="priority:asc">Priority</option>
            <option value="created_at:desc">Recently Created</option>
          </select>
        </div>
        <button className="btn btn-secondary" onClick={() => fetchTasks()}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Tasks Table (List Mode) */}
      {viewMode === 'list' && (
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Task Title & Description</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Related Obligation</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Status</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Priority</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Due Date</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Assignee</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
                    <RefreshCw className="spin" size={24} style={{ margin: '0 auto 8px auto', display: 'block' }} />
                    Loading tasks board...
                  </td>
                </tr>
              ) : !tasksData || tasksData.items.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: '48px', textAlign: 'center' }}>
                    <CheckSquare size={36} style={{ color: '#94a3b8', margin: '0 auto 8px auto' }} />
                    <div style={{ fontWeight: 600, color: '#1e293b' }}>No remediation tasks found</div>
                    <div style={{ fontSize: '13px', color: '#64748b', marginTop: '4px' }}>
                      All compliance obligations are currently up to date, or no tasks match your filters.
                    </div>
                  </td>
                </tr>
              ) : (
                tasksData.items.map((task) => (
                  <tr
                    key={task.id}
                    style={{ borderBottom: '1px solid #f1f5f9', cursor: 'pointer' }}
                    className="table-row-hover"
                    onClick={() => handleOpenDetail(task)}
                  >
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ fontWeight: 600, color: '#0f172a' }}>{task.title}</div>
                      {task.description && (
                        <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>
                          {task.description.length > 70 ? `${task.description.slice(0, 70)}...` : task.description}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      {task.requirement_code ? (
                        <span className="badge badge-neutral">{task.requirement_code}</span>
                      ) : (
                        <span style={{ color: '#94a3b8' }}>General Facility</span>
                      )}
                    </td>
                    <td style={{ padding: '14px 16px' }}>{renderStatusBadge(task.status)}</td>
                    <td style={{ padding: '14px 16px' }}>{renderPriorityBadge(task.priority)}</td>
                    <td style={{ padding: '14px 16px', color: '#334155' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <Calendar size={13} style={{ color: '#64748b' }} />
                        {task.due_date}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px', color: '#475569' }}>
                      {task.assigned_to_name || task.assigned_to_email || 'Unassigned'}
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenDetail(task);
                        }}
                      >
                        Manage
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {/* Pagination Bar */}
          {tasksData && tasksData.total > 0 && (
            <div
              style={{
                padding: '12px 16px',
                borderTop: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: '#f8fafc',
                fontSize: '13px',
                color: '#64748b',
              }}
            >
              <div>
                Showing <strong>{(page - 1) * pageSize + 1}</strong> to{' '}
                <strong>{Math.min(page * pageSize, tasksData.total)}</strong> of{' '}
                <strong>{tasksData.total}</strong> remediation tasks
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button
                  className="btn btn-secondary btn-sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft size={14} /> Previous
                </button>
                <span>
                  Page <strong>{page}</strong> of <strong>{tasksData.total_pages}</strong>
                </span>
                <button
                  className="btn btn-secondary btn-sm"
                  disabled={page >= tasksData.total_pages}
                  onClick={() => setPage((p) => Math.min(tasksData.total_pages, p + 1))}
                >
                  Next <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Calendar View Mode */}
      {viewMode === 'calendar' && (
        <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '20px' }}>
          {/* Calendar Month Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#0f172a', margin: 0 }}>
                {calendarMonth.toLocaleString('default', { month: 'long', year: 'numeric' })}
              </h2>
              <span className="badge badge-neutral" style={{ fontSize: '11px' }}>
                {tasksData?.items.filter((t) => {
                  const d = new Date(t.due_date);
                  return (
                    d.getFullYear() === calendarMonth.getFullYear() &&
                    d.getMonth() === calendarMonth.getMonth()
                  );
                }).length || 0}{' '}
                scheduled this month
              </span>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() =>
                  setCalendarMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))
                }
              >
                <ChevronLeft size={14} /> Prev Month
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setCalendarMonth(new Date(2025, 9, 1))}
              >
                Oct 2025 (Demo)
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() =>
                  setCalendarMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))
                }
              >
                Next Month <ChevronRight size={14} />
              </button>
            </div>
          </div>

          {/* Calendar Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(7, 1fr)',
              gap: '1px',
              background: '#e2e8f0',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              overflow: 'hidden',
            }}
          >
            {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((dayName) => (
              <div
                key={dayName}
                style={{
                  background: '#f8fafc',
                  padding: '10px 8px',
                  textAlign: 'center',
                  fontWeight: 600,
                  fontSize: '12px',
                  color: '#64748b',
                }}
              >
                {dayName}
              </div>
            ))}
            {/* Days generator */}
            {(() => {
              const year = calendarMonth.getFullYear();
              const month = calendarMonth.getMonth();
              const firstDayIndex = (new Date(year, month, 1).getDay() + 6) % 7; // Monday = 0
              const daysInMonth = new Date(year, month + 1, 0).getDate();
              const prevMonthDays = new Date(year, month, 0).getDate();
              const totalCells = Math.ceil((firstDayIndex + daysInMonth) / 7) * 7;

              const cells = [];
              for (let i = 0; i < totalCells; i++) {
                if (i < firstDayIndex) {
                  const prevDay = prevMonthDays - firstDayIndex + i + 1;
                  cells.push(
                    <div
                      key={`prev-${i}`}
                      style={{ background: '#f8fafc', minHeight: '105px', padding: '6px', opacity: 0.4 }}
                    >
                      <span style={{ fontSize: '11px', color: '#94a3b8' }}>{prevDay}</span>
                    </div>
                  );
                } else if (i < firstDayIndex + daysInMonth) {
                  const dayNum = i - firstDayIndex + 1;
                  const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
                  const dayTasks = (tasksData?.items || []).filter((t) => t.due_date === dateStr);
                  const isToday = dayNum === 24 && month === 9 && year === 2025;

                  cells.push(
                    <div
                      key={`day-${dayNum}`}
                      style={{
                        background: isToday ? '#f0fdf4' : '#ffffff',
                        minHeight: '105px',
                        padding: '6px',
                        border: isToday ? '1px solid #86efac' : 'none',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span
                          style={{
                            fontSize: '12px',
                            fontWeight: isToday ? 700 : 500,
                            color: isToday ? '#059669' : '#1e293b',
                          }}
                        >
                          {dayNum} {isToday && '• Today'}
                        </span>
                        {dayTasks.length > 0 && (
                          <span
                            style={{
                              fontSize: '10px',
                              fontWeight: 600,
                              color: '#059669',
                              background: '#ecfdf5',
                              borderRadius: '10px',
                              padding: '0 5px',
                            }}
                          >
                            {dayTasks.length}
                          </span>
                        )}
                      </div>
                      <div
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '3px',
                          marginTop: '2px',
                          overflow: 'hidden',
                        }}
                      >
                        {dayTasks.slice(0, 3).map((task) => {
                          const isHigh = task.priority === 'HIGH';
                          const isCompleted = task.status === 'COMPLETED';
                          return (
                            <div
                              key={task.id}
                              onClick={() => handleOpenDetail(task)}
                              title={`${task.title} (${task.status})`}
                              style={{
                                fontSize: '10.5px',
                                padding: '3px 6px',
                                borderRadius: '4px',
                                background: isCompleted ? '#f1f5f9' : isHigh ? '#fef2f2' : '#f0fdf4',
                                color: isCompleted ? '#64748b' : isHigh ? '#b91c1c' : '#15803d',
                                borderLeft: `3px solid ${isCompleted ? '#94a3b8' : isHigh ? '#dc2626' : '#16a34a'}`,
                                cursor: 'pointer',
                                whiteSpace: 'nowrap',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                textDecoration: isCompleted ? 'line-through' : 'none',
                              }}
                            >
                              {task.title}
                            </div>
                          );
                        })}
                        {dayTasks.length > 3 && (
                          <div style={{ fontSize: '10px', color: '#64748b', textAlign: 'center' }}>
                            +{dayTasks.length - 3} more
                          </div>
                        )}
                      </div>
                    </div>
                  );
                } else {
                  const nextDay = i - (firstDayIndex + daysInMonth) + 1;
                  cells.push(
                    <div
                      key={`next-${i}`}
                      style={{ background: '#f8fafc', minHeight: '105px', padding: '6px', opacity: 0.4 }}
                    >
                      <span style={{ fontSize: '11px', color: '#94a3b8' }}>{nextDay}</span>
                    </div>
                  );
                }
              }
              return cells;
            })()}
          </div>
        </div>
      )}

      {/* Task Detail & State Transition Drawer */}
      {selectedTask && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.45)',
            backdropFilter: 'blur(2px)',
            zIndex: 1000,
            display: 'flex',
            justifyContent: 'flex-end',
          }}
          onClick={() => setSelectedTask(null)}
        >
          <div
            style={{
              width: '560px',
              maxWidth: '90vw',
              background: '#ffffff',
              height: '100%',
              overflowY: 'auto',
              boxShadow: '-4px 0 24px rgba(0,0,0,0.15)',
              display: 'flex',
              flexDirection: 'column',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Drawer Header */}
            <div
              style={{
                padding: '20px 24px',
                borderBottom: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                background: '#06281e',
                color: '#ffffff',
              }}
            >
              <div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '4px' }}>
                  {renderPriorityBadge(selectedTask.priority)}
                  {renderStatusBadge(selectedTask.status)}
                </div>
                <h2 style={{ fontSize: '18px', fontWeight: 600, margin: 0, color: '#ffffff' }}>
                  {selectedTask.title}
                  {detailLoading && (
                    <span style={{ fontSize: '11px', color: '#6ee7b7', marginLeft: '8px', fontWeight: 400 }}>
                      (Refreshing...)
                    </span>
                  )}
                </h2>
              </div>
              <button
                onClick={() => setSelectedTask(null)}
                style={{ background: 'transparent', border: 'none', color: '#ffffff', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Drawer Body */}
            <div style={{ padding: '24px', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Controlled Transition Bar */}
              <div
                style={{
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  padding: '16px',
                }}
              >
                <div style={{ fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '8px' }}>
                  Controlled State Actions
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {selectedTask.status === 'TODO' && (
                    <>
                      <button
                        className="btn btn-primary btn-sm"
                        disabled={transitioning}
                        onClick={() => handleStatusTransition('IN_PROGRESS', 'Work started on remediation.')}
                      >
                        Start Work (In Progress)
                      </button>
                      <button
                        className="btn btn-critical btn-sm"
                        disabled={transitioning}
                        onClick={() => setShowBlockModal(true)}
                      >
                        Mark Blocked
                      </button>
                    </>
                  )}

                  {selectedTask.status === 'IN_PROGRESS' && (
                    <>
                      <button
                        className="btn btn-primary btn-sm"
                        disabled={transitioning}
                        onClick={() => handleStatusTransition('COMPLETED', 'Remediation completed and verified.')}
                      >
                        Mark Resolved (Completed)
                      </button>
                      <button
                        className="btn btn-critical btn-sm"
                        disabled={transitioning}
                        onClick={() => setShowBlockModal(true)}
                      >
                        Mark Blocked
                      </button>
                    </>
                  )}

                  {selectedTask.status === 'BLOCKED' && (
                    <>
                      <button
                        className="btn btn-primary btn-sm"
                        disabled={transitioning}
                        onClick={() => handleStatusTransition('IN_PROGRESS', 'Blockage resolved, resuming work.')}
                      >
                        Unblock & Resume (In Progress)
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        disabled={transitioning}
                        onClick={() => handleStatusTransition('TODO', 'Moved back to backlog.')}
                      >
                        Back to To Do
                      </button>
                    </>
                  )}

                  {selectedTask.status === 'COMPLETED' && (
                    <button
                      className="btn btn-secondary btn-sm"
                      disabled={transitioning}
                      onClick={() => handleStatusTransition('IN_PROGRESS', 'Reopened for additional inspection.')}
                    >
                      Reopen Task
                    </button>
                  )}
                </div>

                {selectedTask.blocked_reason && (
                  <div
                    style={{
                      marginTop: '12px',
                      background: '#fff1f2',
                      border: '1px solid #fecdd3',
                      borderRadius: '6px',
                      padding: '10px 12px',
                      color: '#9f1239',
                      fontSize: '12px',
                    }}
                  >
                    <strong>Current Blockage Reason:</strong> {selectedTask.blocked_reason}
                  </div>
                )}
              </div>

              {/* Task Metadata */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '12px',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '14px',
                  fontSize: '13px',
                }}
              >
                <div>
                  <div style={{ color: '#64748b', fontSize: '11px', fontWeight: 600 }}>Due Date</div>
                  <div style={{ color: '#1e293b', fontWeight: 500, marginTop: '2px' }}>{selectedTask.due_date}</div>
                </div>
                <div>
                  <div style={{ color: '#64748b', fontSize: '11px', fontWeight: 600 }}>Assignee</div>
                  <div style={{ color: '#1e293b', fontWeight: 500, marginTop: '2px' }}>
                    {selectedTask.assigned_to_name || selectedTask.assigned_to_email || 'Unassigned'}
                  </div>
                </div>
                {selectedTask.requirement_code && (
                  <div style={{ gridColumn: 'span 2' }}>
                    <div style={{ color: '#64748b', fontSize: '11px', fontWeight: 600 }}>Governing Requirement</div>
                    <div style={{ color: '#1e293b', fontWeight: 500, marginTop: '2px' }}>
                      <strong>{selectedTask.requirement_code}</strong>: {selectedTask.requirement_title}
                    </div>
                  </div>
                )}
              </div>

              {/* Description */}
              {selectedTask.description && (
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                    Remediation Scope & Instructions
                  </div>
                  <p style={{ margin: 0, fontSize: '13px', color: '#1e293b', lineHeight: 1.5, background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '12px' }}>
                    {selectedTask.description}
                  </p>
                </div>
              )}

              {/* Activity / Comments Stream */}
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#1e293b', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <MessageSquare size={15} style={{ color: '#059669' }} /> Activity Stream & Comments ({selectedTask.comments?.length || 0})
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
                  {selectedTask.comments && selectedTask.comments.length > 0 ? (
                    selectedTask.comments.map((c) => (
                      <div
                        key={c.id}
                        style={{
                          background: '#f8fafc',
                          border: '1px solid #e2e8f0',
                          borderRadius: '6px',
                          padding: '10px 12px',
                          fontSize: '12px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748b', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 600, color: '#334155' }}>{c.user_name || 'System / Auditor'}</span>
                          <span>{new Date(c.created_at).toLocaleDateString()}</span>
                        </div>
                        <div style={{ color: '#1e293b' }}>{c.comment_text}</div>
                      </div>
                    ))
                  ) : (
                    <div style={{ fontSize: '12px', color: '#94a3b8', fontStyle: 'italic' }}>
                      No comments recorded yet.
                    </div>
                  )}
                </div>

                {/* Add Comment Form */}
                <form onSubmit={handleAddComment} style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    className="input-field"
                    placeholder="Add operational note or verification update..."
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    style={{ flex: 1, fontSize: '13px' }}
                  />
                  <button type="submit" className="btn btn-secondary btn-sm" disabled={commentSubmitting || !newComment.trim()}>
                    <Send size={13} />
                  </button>
                </form>
              </div>

              {/* Attachments Section */}
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#1e293b', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Paperclip size={15} style={{ color: '#059669' }} /> Linked Evidence & Attachments ({selectedTask.attachments?.length || 0})
                </h3>
                {selectedTask.attachments && selectedTask.attachments.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {selectedTask.attachments.map((a) => (
                      <div
                        key={a.id}
                        style={{
                          border: '1px solid #e2e8f0',
                          borderRadius: '6px',
                          padding: '8px 12px',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          fontSize: '12px',
                        }}
                      >
                        <span style={{ fontWeight: 500, color: '#0f172a' }}>{a.filename}</span>
                        <span style={{ color: '#64748b' }}>{(a.file_size_bytes / 1024).toFixed(1)} KB</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '12px', color: '#94a3b8', fontStyle: 'italic' }}>
                    No documents attached to this task.
                  </div>
                )}
              </div>
            </div>

            {/* Drawer Footer */}
            <div style={{ padding: '16px 24px', borderTop: '1px solid #e2e8f0', background: '#f8fafc', textAlign: 'right' }}>
              <button className="btn btn-secondary" onClick={() => setSelectedTask(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mandatory Blocked Reason Modal */}
      {showBlockModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1100,
          }}
        >
          <div style={{ width: '440px', maxWidth: '95vw', background: '#ffffff', borderRadius: '8px', padding: '24px' }}>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: 600, color: '#991b1b', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} /> Mandatory Blockage Explanation
            </h3>
            <p style={{ margin: '0 0 14px 0', fontSize: '13px', color: '#475569' }}>
              Under PlantProof compliance rules, marking a task as BLOCKED strictly requires an operational reason (e.g. vendor delay, regulator clarification, spare part lead time).
            </p>
            <textarea
              className="input-field"
              rows={3}
              required
              placeholder="Explain why work cannot proceed..."
              value={blockedReason}
              onChange={(e) => setBlockedReason(e.target.value)}
              style={{ width: '100%', fontSize: '13px', marginBottom: '16px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button className="btn btn-secondary" onClick={() => setShowBlockModal(false)}>
                Cancel
              </button>
              <button
                className="btn btn-critical"
                disabled={!blockedReason.trim() || transitioning}
                onClick={() => handleStatusTransition('BLOCKED', blockedReason.trim())}
              >
                Confirm Blocked Status
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Task Modal */}
      {showCreateModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1100,
          }}
        >
          <div style={{ width: '480px', maxWidth: '95vw', background: '#ffffff', borderRadius: '8px', padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600 }}>New Remediation Task</h3>
              <button onClick={() => setShowCreateModal(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateTask}>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                  Task Title
                </label>
                <input
                  type="text"
                  className="input-field"
                  required
                  placeholder="e.g. Renew Hazardous Waste Authorization"
                  value={createTitle}
                  onChange={(e) => setCreateTitle(e.target.value)}
                  style={{ width: '100%', fontSize: '13px' }}
                />
              </div>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                  Description / Action Items
                </label>
                <textarea
                  className="input-field"
                  rows={2}
                  placeholder="Detailed instructions for site engineers..."
                  value={createDesc}
                  onChange={(e) => setCreateDesc(e.target.value)}
                  style={{ width: '100%', fontSize: '13px' }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                    Target Due Date
                  </label>
                  <input
                    type="date"
                    className="input-field"
                    required
                    value={createDueDate}
                    onChange={(e) => setCreateDueDate(e.target.value)}
                    style={{ width: '100%', fontSize: '13px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>
                    Priority
                  </label>
                  <select
                    className="input-field"
                    value={createPriority}
                    onChange={(e) => setCreatePriority(e.target.value as 'HIGH' | 'MEDIUM' | 'LOW')}
                    style={{ width: '100%', fontSize: '13px' }}
                  >
                    <option value="HIGH">High Priority</option>
                    <option value="MEDIUM">Medium Priority</option>
                    <option value="LOW">Low Priority</option>
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={createSubmitting}>
                  {createSubmitting ? 'Creating...' : 'Schedule Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
