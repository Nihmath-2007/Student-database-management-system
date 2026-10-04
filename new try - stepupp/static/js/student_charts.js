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
                if (id === 'stuKpiBest' || id === 'stuKpiLowest') {
                    el.title = text;
                    const card = el.closest('.kpi-card');
                    if (card) card.title = text;
                }
            }
        };

        if (data.profile && data.profile.name) {
            setEl('heroStudentName', data.profile.name);
        }
        setEl('stuKpiAtt', `${data.attendance ? data.attendance.attendance_percentage : 0}%`);
        setEl('stuKpiAvg', `${data.overall_average || 0}%`);
        setEl('stuKpiPass', data.passed_subjects || 0);
        setEl('stuKpiFail', data.failed_subjects || 0);
        const subjects = data.subjects || [];
        const getShort = (name) => (window.getSubjectShortName ? window.getSubjectShortName(name) : name);
        
        const bestSub = data.best_subject || 'N/A';
        const lowestSub = data.lowest_subject || 'N/A';
        setEl('stuKpiBest', getShort(bestSub));
        setEl('stuKpiLowest', getShort(lowestSub));

        const subShortLabels = subjects.map(s => s.short_name || getShort(s.subject_name));
        const subFullNames = subjects.map(s => s.subject_name);
        const subMarks = subjects.map(s => s.percentage);

        // 1. Marks Bar Chart (Slim horizontal straight labels, custom palette)
        const canvasM = document.getElementById('myMarksChart');
        if (canvasM) {
            const ctxM = canvasM.getContext('2d');
            if (myMarksChartInstance) myMarksChartInstance.destroy();
            myMarksChartInstance = new Chart(ctxM, {
                type: 'bar',
                data: {
                    labels: subShortLabels,
                    datasets: [{
                        label: 'Marks obtained (%)',
                        data: subMarks,
                        backgroundColor: '#f25822',
                        borderColor: '#e04713',
                        borderWidth: 1,
                        borderRadius: 6,
                        barPercentage: 0.45,
                        categoryPercentage: 0.65,
                        maxBarThickness: 36
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#131d3b',
                            titleColor: '#ffffff',
                            bodyColor: '#f1f5f9',
                            borderColor: '#f25822',
                            borderWidth: 1,
                            padding: 10,
                            cornerRadius: 6,
                            callbacks: {
                                title: function(items) {
                                    if (!items.length) return '';
                                    const idx = items[0].dataIndex;
                                    const code = subjects[idx]?.subject_code ? ` (${subjects[idx].subject_code})` : '';
                                    return (subFullNames[idx] || subShortLabels[idx]) + code;
                                },
                                label: function(item) {
                                    return `Marks: ${item.raw}%`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: {
                                autoSkip: false, // Ensure every subject name is displayed without skipping
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
