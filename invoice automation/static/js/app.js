// static/js/app.js
document.addEventListener("DOMContentLoaded", () => {
  console.log("✅ app.js loaded");

  // ===== COUNTER ANIMATION =====
  document.querySelectorAll(".counter").forEach(counter => {
    const target = parseFloat(counter.dataset.target) || 0;
    let current = 0;
    const steps = 100;
    const increment = target / steps;

    function update() {
      current += increment;
      if (current < target) {
        counter.innerText = Number.isInteger(target)
          ? Math.floor(current)
          : current.toFixed(2);
        requestAnimationFrame(update);
      } else {
        counter.innerText = Number.isInteger(target)
          ? target
          : target.toFixed(2);
      }
    }
    update();
  });

  // ===== DASHBOARD: Paid vs Unpaid Line Chart =====
  const dashboardEl = document.getElementById("revenueChart");
  if (dashboardEl) {
    fetch("/api/monthly-revenue-status")
      .then(res => res.json())
      .then(data => {
        const palette = {
          paid: "#28a745",
          unpaid: "#dc3545",
          mutedGrid: "rgba(255,255,255,0.06)"
        };

        new Chart(dashboardEl, {
          type: "line",
          data: {
            labels: data.labels,
            datasets: [
              {
                label: "Paid Revenue",
                data: data.paid,
                borderColor: palette.paid,
                backgroundColor: "rgba(40,167,69,0.3)",
                tension: 0.35,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 7
              },
              {
                label: "Unpaid Revenue",
                data: data.unpaid,
                borderColor: palette.unpaid,
                backgroundColor: "rgba(220,53,69,0.3)",
                tension: 0.35,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 7
              }
            ]
          },
          options: {
            responsive: true,
            plugins: {
              legend: { position: "top", labels: { color: "#cfd3e0" } },
              title: { display: true, text: "Monthly Revenue (Paid vs Unpaid)", color: "#fff" },
              tooltip: {
                callbacks: {
                  label: (ctx) => ` $${Number(ctx.raw).toLocaleString()}`
                }
              }
            },
            scales: {
              x: { ticks: { color: "#cfd3e0" }, grid: { color: palette.mutedGrid } },
              y: { beginAtZero: true, ticks: { color: "#cfd3e0" }, grid: { color: palette.mutedGrid } }
            }
          }
        });
      })
      .catch(err => console.error("❌ Dashboard chart error:", err));
  }

  // ===== REPORTS PAGE =====
  const reportData = window.reportData || {};
  const monthlyRevenue = Array.isArray(reportData.monthly_revenue) ? reportData.monthly_revenue : [];
  const paidVsUnpaid = reportData.paid_vs_unpaid || {};
  const topClients = reportData.top_clients || {};

  const palette = {
    primary: "#0d6efd",
    success: "#28a745",
    danger: "#dc3545",
    mutedGrid: "rgba(255,255,255,0.06)"
  };

  // --- Monthly Revenue Line Chart (Reports) ---
  const revenueEl = document.getElementById("reportRevenueChart");
  if (revenueEl) {
    const labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const ctx = revenueEl.getContext("2d");
    new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Revenue",
          data: monthlyRevenue,
          borderColor: palette.primary,
          backgroundColor: "rgba(13,110,253,0.2)",
          tension: 0.35,
          fill: true,
          pointRadius: 3,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#cfd3e0" }, grid: { color: palette.mutedGrid } },
          y: { beginAtZero: true, ticks: { color: "#cfd3e0" }, grid: { color: palette.mutedGrid } }
        }
      }
    });
  }

  // --- Paid vs Unpaid Pie Chart (Reports) ---
  const statusEl = document.getElementById("statusChart");
  if (statusEl) {
    const keys = Object.keys(paidVsUnpaid);
    const values = Object.values(paidVsUnpaid);

    new Chart(statusEl, {
      type: "doughnut",
      data: { labels: keys, datasets: [{ data: values, backgroundColor: [palette.success, palette.danger] }] },
      options: { responsive: true, cutout: "55%", plugins: { legend: { position: "bottom" } } }
    });
  }

  // --- Top Clients Bar Chart (Reports) ---
  const clientsEl = document.getElementById("clientsChart");
  if (clientsEl) {
    const labels = Object.keys(topClients);
    const values = Object.values(topClients);

    new Chart(clientsEl, {
      type: "bar",
      data: { labels, datasets: [{ label: "Revenue", data: values, backgroundColor: "rgba(54,162,235,0.85)" }] },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#cfd3e0" }, grid: { color: palette.mutedGrid } },
          y: { beginAtZero: true, ticks: { color: "#cfd3e0" }, grid: { color: palette.mutedGrid } }
        }
      }
    });
  }
});
