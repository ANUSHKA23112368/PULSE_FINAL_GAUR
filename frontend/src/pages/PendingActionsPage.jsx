import React, { useState, useEffect } from 'react';
import {
  ListTodo,
  Clock,
  CheckCircle2,
  AlertCircle,
  Plus,
  RefreshCw,
  Check,
  RotateCcw
} from 'lucide-react';
import { PatientBanner } from '../components/PatientBanner';
import {
  fetchPatientTasks,
  createPatientTask,
  updatePatientTask
} from '../services/api';

export function PendingActionsPage({ selectedPatient, onSwitchPatient, onNavigate, allPatients, onSelectPatient }) {
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
      const evidenceText = `Status updated to ${newStatus} by Staff Clinician at ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
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
      {/* Patient Banner */}
      <PatientBanner
        patient={selectedPatient}
        onSwitchPatient={onSwitchPatient}
        allPatients={allPatients}
        onSelectPatient={onSelectPatient}
        onNavigate={onNavigate}
      />

      {/* Page Title & Controls */}
      <div className="section-header-row">
        <div>
          <h2 className="page-heading">
            Shift Action Tracker & Clinical Directives
          </h2>
          <p className="page-subheading">
            Persistent follow-up orders, scheduled rechecks, pending labs, and consultations for <strong>{selectedPatient?.name || 'patient'}</strong>.
          </p>
        </div>

        <div className="header-actions-group">
          <button
            onClick={() => setShowAddModal(true)}
            className="btn btn-primary"
          >
            <Plus size={15} />
            <span>Add Task</span>
          </button>

          <button
            onClick={loadTasks}
            disabled={loading}
            className="btn btn-outline"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {feedback && (
        <div className={`feedback-alert feedback-${feedback.type}`}>
          {feedback.type === 'success' ? <CheckCircle2 size={16} className="text-emerald" /> : <AlertCircle size={16} className="text-rose" />}
          <span>{feedback.text}</span>
          <button className="feedback-close" onClick={() => setFeedback(null)}>×</button>
        </div>
      )}

      {/* Filter Tabs Strip */}
      <div className="hospital-card task-filter-card">
        <div className="filter-pills-row">
          <button
            className={`filter-pill ${filter === 'ALL' ? 'active' : ''}`}
            onClick={() => setFilter('ALL')}
          >
            All Tasks ({counts.all})
          </button>
          <button
            className={`filter-pill filter-pending ${filter === 'PENDING' ? 'active' : ''}`}
            onClick={() => setFilter('PENDING')}
          >
            Pending ({counts.pending})
          </button>
          <button
            className={`filter-pill filter-completed ${filter === 'COMPLETED' ? 'active' : ''}`}
            onClick={() => setFilter('COMPLETED')}
          >
            Completed ({counts.completed})
          </button>
          <button
            className={`filter-pill filter-review ${filter === 'NEEDS_REVIEW' ? 'active' : ''}`}
            onClick={() => setFilter('NEEDS_REVIEW')}
          >
            Needs Review ({counts.needs_review})
          </button>
        </div>
      </div>

      {/* Tasks Content List */}
      {loading ? (
        <div className="hospital-card loading-state-card">
          <RefreshCw size={24} className="animate-spin text-primary" />
          <span>Loading clinical tasks...</span>
        </div>
      ) : filteredTasks.length === 0 ? (
        <div className="hospital-card empty-state-card">
          <ListTodo size={36} className="text-muted" />
          <h3>No tasks in this category</h3>
          <p>Click "Add Task" to record a new follow-up order for this shift.</p>
        </div>
      ) : (
        <div className="tasks-grid">
          {filteredTasks.map((t) => {
            const isCompleted = t.status === 'Completed';
            const isPending = t.status === 'Pending';
            const isReview = t.status === 'Needs Review';
            const priorityClass = (t.priority || 'Medium').toLowerCase();

            return (
              <div 
                key={t.id} 
                className={`hospital-card task-card task-card-${isCompleted ? 'completed' : isReview ? 'review' : 'active'}`}
              >
                <div className="task-header-row">
                  <div className="task-tags">
                    <span className="task-id-badge">#{t.id}</span>
                    <span className={`priority-pill priority-${priorityClass}`}>
                      {t.priority || 'Medium'} Priority
                    </span>
                    <span className={`status-pill status-${t.status.toLowerCase().replace(' ', '-')}`}>
                      {t.status}
                    </span>
                  </div>

                  {t.due_time && (
                    <div className="task-due-time">
                      <Clock size={13} />
                      <span>Due: {t.due_time}</span>
                    </div>
                  )}
                </div>

                <div className="task-body">
                  <p className={`task-text ${isCompleted ? 'text-strikethrough' : ''}`}>
                    {t.task}
                  </p>
                  {t.evidence && (
                    <div className="task-evidence-box">
                      <strong>Audit Trail:</strong> {t.evidence}
                    </div>
                  )}
                </div>

                <div className="task-footer">
                  <span className="task-source-label">
                    {t.type || 'Clinical Handover Task'}
                  </span>

                  <div className="task-status-actions">
                    {isPending && (
                      <>
                        <button
                          type="button"
                          className="btn btn-outline btn-xs"
                          onClick={() => handleStatusChange(t.id, 'Needs Review')}
                        >
                          Mark for Review
                        </button>
                        <button
                          type="button"
                          className="btn btn-primary btn-xs"
                          onClick={() => handleStatusChange(t.id, 'Completed')}
                        >
                          <Check size={12} /> Complete
                        </button>
                      </>
                    )}

                    {isCompleted && (
                      <button
                        type="button"
                        className="btn btn-outline btn-xs"
                        onClick={() => handleStatusChange(t.id, 'Pending')}
                      >
                        <RotateCcw size={12} /> Reopen
                      </button>
                    )}

                    {isReview && (
                      <>
                        <button
                          type="button"
                          className="btn btn-outline btn-xs"
                          onClick={() => handleStatusChange(t.id, 'Pending')}
                        >
                          Return to Pending
                        </button>
                        <button
                          type="button"
                          className="btn btn-primary btn-xs"
                          onClick={() => handleStatusChange(t.id, 'Completed')}
                        >
                          <Check size={12} /> Verify & Complete
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Task Modal */}
      {showAddModal && (
        <div className="modal-backdrop" onClick={() => setShowAddModal(false)}>
          <div className="add-task-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-group">
                <Plus size={20} className="modal-icon text-primary" />
                <h3>Add Shift Action or Pending Directive</h3>
              </div>
              <button className="modal-close-btn" onClick={() => setShowAddModal(false)}>×</button>
            </div>

            <form onSubmit={handleAddTask}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Task Description *</label>
                  <textarea
                    rows={3}
                    className="form-input"
                    placeholder="e.g. Check morning blood glucose at 0600; follow-up repeat troponin report..."
                    value={newTaskText}
                    onChange={(e) => setNewTaskText(e.target.value)}
                    required
                  />
                </div>

                <div className="form-grid-2col">
                  <div className="form-group">
                    <label className="form-label">Priority</label>
                    <select
                      className="form-input"
                      value={newPriority}
                      onChange={(e) => setNewPriority(e.target.value)}
                    >
                      <option value="STAT / Urgent">STAT / Urgent</option>
                      <option value="High">High</option>
                      <option value="Medium">Medium</option>
                      <option value="Low">Low</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Scheduled Due Time (Optional)</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. 12:00 PM / End of Shift"
                      value={newDueTime}
                      onChange={(e) => setNewDueTime(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="modal-action-btn secondary"
                  onClick={() => setShowAddModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="modal-action-btn primary"
                  disabled={savingTask}
                >
                  {savingTask ? 'Saving Task...' : '+ Record Directive'}
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
