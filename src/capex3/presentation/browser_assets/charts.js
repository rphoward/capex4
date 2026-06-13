(function () {
  "use strict";

  function formatMoneyK(value) {
    if (typeof value !== "number" || Number.isNaN(value)) {
      return "-";
    }
    var prefix = value < 0 ? "-$" : "$";
    var magnitude = Math.abs(value);
    if (magnitude >= 1000000) {
      return prefix + (magnitude / 1000000).toFixed(1) + "M";
    }
    if (magnitude >= 1000) {
      return prefix + Math.round(magnitude / 1000) + "k";
    }
    return prefix + Math.round(magnitude);
  }

  function applyClientOptions(config) {
    var yAxisList = Array.isArray(config.yAxis) ? config.yAxis : [config.yAxis || {}];
    yAxisList.forEach(function (axis) {
      if (axis && axis.labels && axis.labels.__format === "moneyK") {
        axis.labels.formatter = function () {
          return formatMoneyK(this.value);
        };
        delete axis.labels.__format;
      }
    });
    config.yAxis = yAxisList.length === 1 ? yAxisList[0] : yAxisList;

    (config.series || []).forEach(function (series) {
      if (series.dataLabels && series.dataLabels.__format === "moneyK") {
        series.dataLabels.formatter = function () {
          if (series.dataLabels.__lastPointOnly && this.point.index !== this.series.data.length - 1) {
            return null;
          }
          return formatMoneyK(this.y);
        };
        delete series.dataLabels.__format;
        delete series.dataLabels.__lastPointOnly;
      }
    });

    if (config.tooltip && config.tooltip.__format === "money") {
      config.tooltip.formatter = function () {
        var points = this.points || [this.point];
        var header = this.x !== undefined ? String(this.x) : "";
        var lines = points.map(function (point) {
          return (
            '<span style="color:' +
            point.color +
            '">\u25CF</span> ' +
            point.series.name +
            ": <b>" +
            formatMoneyK(point.y) +
            "</b>"
          );
        });
        return (header ? header + "<br/>" : "") + lines.join("<br/>");
      };
      delete config.tooltip.__format;
    }

    return config;
  }

  function destroyChart(element) {
    if (element.highchartsChart) {
      element.highchartsChart.destroy();
      element.highchartsChart = null;
    }
  }

  function mountCharts(root) {
    if (!window.Highcharts) {
      return;
    }
    var scope = root || document;
    scope.querySelectorAll("[data-highcharts-config]").forEach(function (element) {
      destroyChart(element);
      var raw = element.getAttribute("data-highcharts-config");
      if (!raw) {
        return;
      }
      try {
        var config = applyClientOptions(JSON.parse(raw));
        element.highchartsChart = Highcharts.chart(element, config);
      } catch (error) {
        element.innerHTML = '<div class="error-text">Chart unavailable.</div>';
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    mountCharts(document);
  });

  document.body.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail && event.detail.target) {
      mountCharts(event.detail.target);
    }
  });
})();
