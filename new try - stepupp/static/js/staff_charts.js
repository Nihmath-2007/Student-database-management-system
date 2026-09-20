/* Staff Dashboard Chart.js Manager */

let staffMarksBarChart = null;
let staffMarksPieChart = null;
let currentStaffDashboardData = null;

async function initStaffDashboard() {
    try {
        const res = await fetch('/staff/api/dashboard');
        currentStaffDashboardData = await res.json();

        const setEl = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val;
        };

        setEl('staffKpiSubjects', currentStaffDashboardData.assigned_subjects_count || 0);
        setEl('staffKpiAvgMarks', `${currentStaffDashboardData.average_marks || 0}%`);

        // Populate dropdown
        const select = document.getElementById('staffSubjectSelect');
        const subjects = currentStaffDashboardData.subjects || [];

        if (!select) return;

        if (subjects.length === 0) {
            select.innerHTML = '<option value="">No subjects assigned</option>';
            return;
        }

        select.innerHTML = subjects.map(s => `<option value="${s.subjectid}">${s.subject_code} - ${s.subject_name}</option>`).join('');

        onStaffSubjectChange();

    } catch (e) {
        console.error('Error loading staff dashboard:', e);
    }
}

async function onStaffSubjectChange() {
    const select = document.getElementById('staffSubjectSelect');
    if (!select) return;
    const subId = select.value;
    if (!subId) return;

    try {
        const res = await fetch(`/staff/api/subject/${subId}`);
        const data = await res.json();

        const studentMarks = data.student_marks || [];
        const studentNames = studentMarks.map(s => s.name.split(' ')[0]);
        const marks = studentMarks.map(s => s.percentage);

        // 1. Student-wise Marks Bar Chart (slim width, horizontal straight labels)
        const canvasM = document.getElementById('staffStudentMarksBar');
        if (canvasM) {
            const ctxM = canvasM.getContext('2d');
            if (staffMarksBarChart) staffMarksBarChart.destroy();
            staffMarksBarChart = new Chart(ctxM, {
                type: 'bar',
                data: {
                    labels: studentNames,
                    datasets: [{
                        label: 'Marks Obtained (%)',
                        data: marks,
                        backgroundColor: '#f25822',
                        borderColor: '#e04713',
                        borderWidth: 1,
                        borderRadius: 6,
                        barPercentage: 0.4,
                        categoryPercentage: 0.6,
                        maxBarThickness: 32
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            ticks: {
                                maxRotation: 0,
                                minRotation: 0,
                                font: { weight: '600', size: 11 }
                            }
                        },
                        y: { min: 0, max: 100, ticks: { callback: v => v + '%' } }
                    }
                }
            });
        }

        // 2. Marks Distribution Pie
        const canvasMPie = document.getElementById('staffMarksPie');
        if (canvasMPie) {
            const ctxMPie = canvasMPie.getContext('2d');
            if (staffMarksPieChart) staffMarksPieChart.destroy();
            staffMarksPieChart = new Chart(ctxMPie, {
                type: 'doughnut',
                data: {
                    labels: ['Passed (>=50%)', 'Failed (<50%)'],
                    datasets: [{
                        data: [data.passed_count || 0, data.failed_count || 0],
                        backgroundColor: ['#047857', '#f43f5e'],
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {
                        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 15 } }
                    }
                }
            });
        }

    } catch (e) {
        console.error('Error updating staff subject charts:', e);
    }
}

document.addEventListener('DOMContentLoaded', initStaffDashboard);
