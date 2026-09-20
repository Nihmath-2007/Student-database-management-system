/* HOD Panel Analytics Chart.js Manager */

let subjectMarksChartInstance = null;
let attPieChartInstance = null;

function shortenSubjectName(name) {
    if (!name) return '';
    const map = {
        'Cloud computing': 'Cloud Comp',
        'Cloud Computing': 'Cloud Comp',
        'Distributed Computing': 'Dist Comp',
        'Embedded System and IOT': 'IoT & Embed',
        'Embedded Systems and IoT': 'IoT & Embed',
        'Foundations of Data Science': 'Data Sci',
        'Full Stack Web Development': 'Full Stack',
        'Full Stack Web Development Laboratory': 'FSWD Lab',
        'UI&UX designing': 'UI/UX',
        'UI&UX Designing': 'UI/UX',
        'UI/UX': 'UI/UX'
    };
    if (map[name]) return map[name];
    if (name.length > 12) {
        return name.split(' ').map(w => w[0]).join('').toUpperCase();
    }
    return name;
}

async function initHodDashboard() {
    try {
        const res = await fetch('/hod/api/analytics');
        const data = await res.json();

        // 1. Populate KPIs safely
        const k = data.kpis || {};
        const setElText = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.innerText = val;
        };

        setElText('kpiTotalStudents', k.total_students || 0);
        setElText('kpiTotalStaff', k.total_staff || 0);
        setElText('kpiTotalSubjects', k.total_subjects || 0);
        setElText('kpiAvgAttendance', `${k.avg_attendance || 0}%`);
        setElText('kpiAvgMarks', `${k.avg_marks || 0}%`);
        setElText('kpiAtRisk', k.at_risk_students || 0);
        setElText('kpiBelow75', k.below_75_attendance || 0);
        setElText('kpiAbove75', k.above_75_attendance || 0);
        setElText('kpiPassRate', `${k.overall_pass_percentage || 0}%`);

        // 2. Render Subject Marks Bar Chart (short form names for maximum spacing)
        const subAnalytics = data.subject_analytics || [];
        const labels = subAnalytics.map(s => shortenSubjectName(s.subject_name));
        const marks = subAnalytics.map(s => s.avg_marks);

        const canvasMarks = document.getElementById('subjectMarksChart');
        if (canvasMarks) {
            const ctxMarks = canvasMarks.getContext('2d');
            if (subjectMarksChartInstance) subjectMarksChartInstance.destroy();
            subjectMarksChartInstance = new Chart(ctxMarks, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Subject Avg Marks (%)',
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

        // 3. Render Attendance Doughnut Chart (neat styling with custom palette)
        const dist = data.attendance_distribution || { below_75: 0, between_75_85: 0, above_85: 0 };
        const canvasPie = document.getElementById('attendancePieChart');
        if (canvasPie) {
            const ctxPie = canvasPie.getContext('2d');
            if (attPieChartInstance) attPieChartInstance.destroy();
            attPieChartInstance = new Chart(ctxPie, {
                type: 'doughnut',
                data: {
                    labels: ['Below 75%', '75% – 85%', 'Above 85%'],
                    datasets: [{
                        data: [dist.below_75, dist.between_75_85, dist.above_85],
                        backgroundColor: ['#f43f5e', '#f59e0b', '#047857'],
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

        // 4. Render Top Performing Students Table (Status column removed)
        const topBody = document.getElementById('topStudentsTable');
        if (topBody) {
            topBody.innerHTML = (data.top_students || []).map(s => `
                <tr onclick="window.location.href='/hod/student/${s.studentid}'" style="cursor: pointer;">
                    <td class="font-monospace fw-bold">${s.regno}</td>
                    <td class="fw-semibold">${s.name}</td>
                    <td>${s.attendance_pct}%</td>
                    <td class="fw-bold text-teal">${s.avg_marks}%</td>
                </tr>
            `).join('');
        }

        // 5. Render At-Risk Students Table (Alert Student action column removed)
        const riskBody = document.getElementById('atRiskStudentsTable');
        if (riskBody) {
            riskBody.innerHTML = (data.at_risk_list || []).map(s => `
                <tr onclick="window.location.href='/hod/student/${s.studentid}'" style="cursor: pointer;">
                    <td class="font-monospace fw-bold">${s.regno}</td>
                    <td class="fw-semibold">${s.name}</td>
                    <td class="text-coral fw-bold">${s.attendance_pct}%</td>
                    <td class="fw-bold">${s.avg_marks}%</td>
                </tr>
            `).join('');
        }

    } catch (err) {
        console.error('Error loading HOD Analytics:', err);
    }
}

document.addEventListener('DOMContentLoaded', initHodDashboard);
