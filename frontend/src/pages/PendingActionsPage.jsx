import React, { useState, useEffect } from 'react';
import {
  ListTodo,
  Clock,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  XCircle,
  Plus,
  RefreshCw,
  FileText,
  ShieldCheck,
  Calendar,
  Filter,
  Check,
  RotateCcw
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import {
  fetchPatientTasks,
  createPatientTask,
  updatePatientTask
} from '../services/api';

export function PendingActionsPage({ selectedPatient, onSwitchPatient, onNavigate }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'PENDING' | 'COMPLETED' | 'NEEDS_REVIEW'
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTaskText, setNewTaskText] = useState('');
  const [newDueTime, setNewDueTime] = useState('');
  const [newPriority, setNewPriority] = useState('Medium');
  const [savingTask, setSavingTask] = useState(false);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    if (selectedPatient) {
      loadTasks();
    }
  }, [selectedPatient]);

  async function loadTasks() {
    if (!selectedPatient) return;
    setLoading(true);
    try {
      const data = await fetchPatientTasks(selectedPatient.display_id || selectedPatient.id);
      setTasks(data.tasks || []);
    } catch (err) {
      console.warn("Could not load tasks:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusChange(taskId, newStatus) {
    if (!selectedPatient) return;
    try {
      const evidenceText = `Status updated to ${newStatus} by Staff Clinician on ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      await updatePatientTask(
        selectedPatient.display_id || selectedPatient.id,
        taskId,
        { status: newStatus, evidence: evidenceText }
      );
      setFeedback({ type: 'success', text: `Task #${taskId} marked as ${newStatus}.` });
      await loadTasks();
    } catch (err) {
      console.error("Task update error:", err);
      setFeedback({ type: 'error', text: 'Failed to update task status.' });
    }
  }

  async function handleAddTask(e) {
    e.preventDefault();
    if (!newTaskText.trim()) return;
    setSavingTask(true);
    setFeedback(null);
    try {
      const pKey = selectedPatient.display_id || selectedPatient.id;
      await createPatientTask(pKey, {
        task: newTaskText.trim(),
        due_time: newDueTime.trim() || null,
        priority: newPriority,
        type: 'Clinician Ordered Pending Task',
        status: 'Pending',
        recorded_time: new Date().toISOString(),
        evidence: `Created manually by Staff Clinician for patient ${selectedPatient.name}`
      });
      setNewTaskText('');
      setNewDueTime('');
      setNewPriority('Medium');
      setShowAddModal(false);
      setFeedback({ type: 'success', text: 'New pending clinical action saved and tracked.' });
      await loadTasks();
    } catch (err) {
      console.error("Failed to add task:", err);
      setFeedback({ type: 'error', text: 'Failed to create task.' });
    } finally {
      setSavingTask(false);
    }
  }

  const counts = {
    all: tasks.length,
    pending: tasks.filter(t => t.status === 'Pending').length,
    completed: tasks.filter(t => t.status === 'Completed').length,
    needs_review: tasks.filter(t => t.status === 'Needs Review').length,
    cancelled: tasks.filter(t => t.status === 'Cancelled').length
  };

  const filteredTasks = tasks.filter(t => {
    if (filter === 'ALL') return true;
    if (filter === 'PENDING') return t.status === 'Pending';
    if (filter === 'COMPLETED') return t.status === 'Completed';
    if (filter === 'NEEDS_REVIEW') return t.status === 'Needs Review';
    if (filter === 'CANCELLED') return t.status === 'Cancelled';
    return true;
  });

  return (
    <div className="page-container">
      {/* Patient Header Banner */}
      <PatientBanner
        patient={selectedPatient}
        onSwitchPatient={onSwitchPatient}
        activeTab="tasks"
        onNavigate={onNavigate}
      />

      {/* Page Title & Controls */}
      <div className="section-header" style={{ marginTop: '1rem', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 600, color: '#1e293b', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
              <ListTodo size={22} color="#059669" />
              Pending Actions & Shift Task Tracker
            </h2>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: '#64748b' }}>
              Persistent follow-up tasks, scheduled rechecks, pending investigations, and clinician directives for <strong>{selectedPatient?.name || 'patient'}</strong>.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              onClick={() => setShowAddModal(true)}
              className="btn-primary"
              style={{ fontSize: '0.8125rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <Plus size={15} />
              Add Pending Task
            </button>

            <button
              onClick={loadTasks}
              disabled={loading}
              className="btn-secondary"
              style={{ fontSize: '0.8125rem', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {feedback && (
        <div style={{
          padding: '0.75rem 1rem',
          borderRadius: '6px',
          marginBottom: '1rem',
          fontSize: '0.875rem',
          background: feedback.type === 'success' ? '#f0fdf4' : '#fef2f2',
          color: feedback.type === 'success' ? '#166534' : '#991b1b',
          border: `1px solid ${feedback.type === 'success' ? '#bbf7d0' : '#fecaca'}`,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <CheckCircle2 size={16} />
          <span>{feedback.text}</span>
        </div>
      )}

      {/* Filter Tabs */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        borderBottom: '1px solid #e2e8f0',
        paddingBottom: '0.75rem',
        marginBottom: '1.25rem',
        flexWrap: 'wrap'
      }}>
        <button
          onClick={() => setFilter('ALL')}
          style={{
            padding: '0.4rem 0.75rem',
            borderRadius: '6px',
            fontSize: '0.8125rem',
            fontWeight: 600,
            border: 'none',
            cursor: 'pointer',
            background: filter === 'ALL' ? '#1e293b' : '#f1f5f9',
            color: filter === 'ALL' ? '#ffffff' : '#475569'
          }}
        >
          All Tasks ({counts.all})
        </button>

        <button
          onClick={() => setFilter('PENDING')}
          style={{
            padding: '0.4rem 0.75rem',
            borderRadius: '6px',
            fontSize: '0.8125rem',
            fontWeight: 600,
            border: 'none',
            cursor: 'pointer',
            background: filter === 'PENDING' ? '#0284c7' : '#f0f9ff',
            color: filter === 'PENDING' ? '#ffffff' : '#0369a1'
          }}
        >
          Pending ({counts.pending})
        </button>

        <button
          onClick={() => setFilter('COMPLETED')}
          style={{
            padding: '0.4rem 0.75rem',
            borderRadius: '6px',
            fontSize: '0.8125rem',
            fontWeight: 600,
            border: 'none',
            cursor: 'pointer',
            background: filter === 'COMPLETED' ? '#16a34a' : '#f0fdf4',
            color: filter === 'COMPLETED' ? '#ffffff' : '#15803d'
          }}
        >
          Completed ({counts.completed})
        </button>

        <button
          onClick={() => setFilter('NEEDS_REVIEW')}
          style={{
            padding: '0.4rem 0.75rem',
            borderRadius: '6px',
            fontSize: '0.8125rem',
            fontWeight: 600,
            border: 'none',
            cursor: 'pointer',
            background: filter === 'NEEDS_REVIEW' ? '#d97706' : '#fffbeb',
            color: filter === 'NEEDS_REVIEW' ? '#ffffff' : '#b45309'
          }}
        >
          Needs Review ({counts.needs_review})
        </button>
      </div>

      {/* Task List */}
      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
          <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.5rem' }} />
          <div>Loading patient tasks...</div>
        </div>
      ) : filteredTasks.length === 0 ? (
        <div style={{
          background: '#ffffff',
          border: '1px dashed #cbd5e1',
          borderRadius: '8px',
          padding: '2.5rem 1.5rem',
          textAlign: 'center',
          maxWidth: '560px',
          margin: '1.5rem auto'
        }}>
          <ListTodo size={36} color="#94a3b8" style={{ margin: '0 auto 0.75rem' }} />
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#1e293b', marginBottom: '0.35rem' }}>
            No {filter !== 'ALL' ? filter.toLowerCase() : ''} tasks found
          </h3>
          <p style={{ fontSize: '0.8125rem', color: '#64748b', marginBottom: '1rem' }}>
            Tasks are automatically extracted from clinical handover notes or manually added by clinicians.
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            className="btn-primary"
            style={{ fontSize: '0.8125rem' }}
          >
            Add First Task
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
          {filteredTasks.map((t) => {
            const isCompleted = t.status === 'Completed';
            const isPending = t.status === 'Pending';
            const isNeedsReview = t.status === 'Needs Review';
            const isCancelled = t.status === 'Cancelled';

            return (
              <div
                key={t.id}
                style={{
                  background: '#ffffff',
                  border: `1px solid ${isCompleted ? '#bbf7d0' : isNeedsReview ? '#fed7aa' : '#e2e8f0'}`,
                  borderLeft: `4px solid ${isCompleted ? '#16a34a' : isNeedsReview ? '#ea580c' : isCancelled ? '#94a3b8' : '#0284c7'}`,
                  borderRadius: '8px',
                  padding: '1rem 1.25rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.625rem'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
                      <span style={{
                        fontSize: '0.9375rem',
                        fontWeight: 600,
                        color: isCompleted ? '#475569' : '#0f172a',
                        textDecoration: isCompleted ? 'line-through' : 'none'
                      }}>
                        {t.task}
                      </span>

                      {/* Status Badge */}
                      <span style={{
                        fontSize: '0.6875rem',
                        fontWeight: 700,
                        padding: '0.15rem 0.5rem',
                        borderRadius: '12px',
                        background: isCompleted ? '#dcfce7' : isPending ? '#e0f2fe' : isNeedsReview ? '#ffedd5' : '#f1f5f9',
                        color: isCompleted ? '#15803d' : isPending ? '#0369a1' : isNeedsReview ? '#c2410c' : '#475569',
                        textTransform: 'uppercase'
                      }}>
                        {t.status}
                      </span>

                      {/* Priority Badge */}
                      {t.priority && (
                        <span style={{
                          fontSize: '0.6875rem',
                          padding: '0.15rem 0.45rem',
                          borderRadius: '4px',
                          background: t.priority === 'High' ? '#fee2e2' : '#f8fafc',
                          color: t.priority === 'High' ? '#b91c1c' : '#64748b',
                          fontWeight: 500
                        }}>
                          {t.priority} Priority
                        </span>
                      )}

                      {/* Due Time */}
                      {t.due_time && (
                        <span style={{
                          fontSize: '0.6875rem',
                          background: '#fef3c7',
                          color: '#92400e',
                          padding: '0.15rem 0.45rem',
                          borderRadius: '4px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          fontWeight: 600
                        }}>
                          <Clock size={11} /> Due: {t.due_time}
                        </span>
                      )}
                    </div>

                    {/* Metadata line */}
                    <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                      <span>Recorded: {new Date(t.recorded_time || t.created_at).toLocaleDateString()} {new Date(t.recorded_time || t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      {t.source_note_id && (
                        <span style={{ color: '#0284c7' }}>Sourced from Note #{t.source_note_id}</span>
                      )}
                    </div>
                  </div>

                  {/* Clinician Action Buttons */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    {isPending && (
                      <button
                        onClick={() => handleStatusChange(t.id, 'Completed')}
                        title="Mark Task Completed"
                        style={{
                          background: '#16a34a',
                          color: '#ffffff',
                          border: 'none',
                          borderRadius: '4px',
                          padding: '0.35rem 0.65rem',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.25rem'
                        }}
                      >
                        <Check size={13} /> Complete
                      </button>
                    )}

                    {isCompleted && (
                      <button
                        onClick={() => handleStatusChange(t.id, 'Pending')}
                        title="Reopen Task as Pending"
                        style={{
                          background: '#f1f5f9',
                          color: '#475569',
                          border: '1px solid #cbd5e1',
                          borderRadius: '4px',
                          padding: '0.35rem 0.55rem',
                          fontSize: '0.75rem',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.25rem'
                        }}
                      >
                        <RotateCcw size={12} /> Reopen
                      </button>
                    )}

                    {!isNeedsReview && !isCompleted && (
                      <button
                        onClick={() => handleStatusChange(t.id, 'Needs Review')}
                        title="Flag for Clinician Clarification"
                        style={{
                          background: '#fffbeb',
                          color: '#b45309',
                          border: '1px solid #fde68a',
                          borderRadius: '4px',
                          padding: '0.35rem 0.55rem',
                          fontSize: '0.75rem',
                          cursor: 'pointer'
                        }}
                      >
                        Needs Review
                      </button>
                    )}

                    {!isCancelled && !isCompleted && (
                      <button
                        onClick={() => handleStatusChange(t.id, 'Cancelled')}
                        title="Cancel Task"
                        style={{
                          background: '#fef2f2',
                          color: '#991b1b',
                          border: '1px solid #fecaca',
                          borderRadius: '4px',
                          padding: '0.35rem 0.55rem',
                          fontSize: '0.75rem',
                          cursor: 'pointer'
                        }}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>

                {/* Evidence Section */}
                {t.evidence && (
                  <div style={{
                    background: '#f8fafc',
                    borderRadius: '4px',
                    padding: '0.5rem 0.75rem',
                    fontSize: '0.75rem',
                    color: '#334155',
                    borderLeft: '3px solid #94a3b8'
                  }}>
                    <strong>Traceable Evidence:</strong> {t.evidence}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Add Task Modal */}
      {showAddModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '1rem'
        }}>
          <div style={{
            background: '#ffffff',
            borderRadius: '8px',
            maxWidth: '500px',
            width: '100%',
            padding: '1.5rem',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
          }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#1e293b', marginTop: 0, marginBottom: '1rem' }}>
              Add Pending Clinical Action
            </h3>

            <form onSubmit={handleAddTask} style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                  Task Description *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Recheck temperature at 12 PM, Repeat troponin at 06:00"
                  value={newTaskText}
                  onChange={(e) => setNewTaskText(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.75rem',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '0.875rem'
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                    Due Time / Interval
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 12:00 PM, In 4 hours"
                    value={newDueTime}
                    onChange={(e) => setNewDueTime(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '6px',
                      border: '1px solid #cbd5e1',
                      fontSize: '0.875rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8125rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>
                    Priority
                  </label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '6px',
                      border: '1px solid #cbd5e1',
                      fontSize: '0.875rem',
                      background: '#ffffff'
                    }}
                  >
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn-secondary"
                  style={{ fontSize: '0.8125rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingTask || !newTaskText.trim()}
                  className="btn-primary"
                  style={{ fontSize: '0.8125rem' }}
                >
                  {savingTask ? 'Saving...' : 'Save Pending Action'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default PendingActionsPage;
