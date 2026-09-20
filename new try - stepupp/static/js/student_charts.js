/* Student Portal Analytics Chart.js Manager */

let myMarksChartInstance = null;
let myPassPieInstance = null;
let myDaysPieInstance = null;

async function initStudentDashboard() {
    try {
        const res = await fetch('/student/api/dashboard');
        const data = await res.json();

        // KPIs
        const setEl = (id, text) => {
            const el = document.getElementById(id);
            if (el) {
                el.innerText = text;
                if (id === 'stuKpiBest' || id === 'stuKpiLowest') el.title = text;
            }
        };

        if (data.profile && data.profile.name) {
            setEl('heroStudentName', data.profile.name);
        }
        setEl('stuKpiAtt', `${data.attendance ? data.attendance.attendance_percentage : 0}%`);
        setEl('stuKpiAvg', `${data.overall_average || 0}%`);
        setEl('stuKpiPass', data.passed_subjects || 0);
        setEl('stuKpiFail', data.failed_subjects || 0);
        setEl('stuKpiBest', data.best_subject || 'N/A');
        setEl('stuKpiLowest', data.lowest_subject || 'N/A');

        const subjects = data.subjects || [];
        const subNames = subjects.map(s => s.subject_name);
        const subMarks = subjects.map(s => s.percentage);

        // 1. Marks Bar Chart (Slim horizontal straight labels, custom palette)
        const canvasM = document.getElementById('myMarksChart');
        if (canvasM) {
            const ctxM = canvasM.getContext('2d');
            if (myMarksChartInstance) myMarksChartInstance.destroy();
            myMarksChartInstance = new Chart(ctxM, {
                type: 'bar',
                data: {
                    labels: subNames,
                    datasets: [{
                        label: 'Marks obtained (%)',
                        data: subMarks,
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

        // 2. Pass Pie Chart
        const canvasP = document.getElementById('myPassPieChart');
        if (canvasP) {
            const ctxP = canvasP.getContext('2d');
            if (myPassPieInstance) myPassPieInstance.destroy();
            myPassPieInstance = new Chart(ctxP, {
                type: 'doughnut',
                data: {
                    labels: ['Passed', 'Failed'],
                    datasets: [{
                        data: [data.passed_subjects || 0, data.failed_subjects || 0],
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

        // 3. Days Ratio Pie Chart
        const canvasD = document.getElementById('myDaysPieChart');
        if (canvasD) {
            const ctxD = canvasD.getContext('2d');
            if (myDaysPieInstance) myDaysPieInstance.destroy();
            myDaysPieInstance = new Chart(ctxD, {
                type: 'pie',
                data: {
                    labels: ['Present Days', 'Absent Days'],
                    datasets: [{
                        data: [data.attendance ? data.attendance.present_days : 0, data.attendance ? data.attendance.absent_days : 0],
                        backgroundColor: ['#0d9488', '#f43f5e'],
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 15 } }
                    }
                }
            });
        }

    } catch (e) {
        console.error('Error loading student dashboard:', e);
    }
}

document.addEventListener('DOMContentLoaded', initStudentDashboard);
