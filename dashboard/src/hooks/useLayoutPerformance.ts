import * as React from 'react';

interface PerformanceMetrics {
  fps: number;
  resizeCount: number;
  averageResizeTime: number;
  lastResizeTime: number;
}

export const useLayoutPerformance = () => {
  const [metrics, setMetrics] = React.useState<PerformanceMetrics>({
    fps: 60,
    resizeCount: 0,
    averageResizeTime: 0,
    lastResizeTime: 0,
  });

  const frameRef = React.useRef<number>();
  const lastFrameTime = React.useRef<number>(performance.now());
  const fpsHistory = React.useRef<number[]>([]);
  const resizeTimes = React.useRef<number[]>([]);

  // FPS monitoring
  const updateFPS = React.useCallback(() => {
    const now = performance.now();
    const delta = now - lastFrameTime.current;
    const fps = Math.round(1000 / delta);

    fpsHistory.current.push(fps);
    if (fpsHistory.current.length > 60) {
      fpsHistory.current.shift();
    }

    const averageFPS = Math.round(
      fpsHistory.current.reduce((sum, f) => sum + f, 0) / fpsHistory.current.length
    );

    lastFrameTime.current = now;
    frameRef.current = requestAnimationFrame(updateFPS);

    setMetrics(prev => ({ ...prev, fps: averageFPS }));
  }, []);

  React.useEffect(() => {
    frameRef.current = requestAnimationFrame(updateFPS);
    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [updateFPS]);

  // Track panel resize performance
  const trackResize = React.useCallback(() => {
    const startTime = performance.now();

    return () => {
      const endTime = performance.now();
      const duration = endTime - startTime;

      resizeTimes.current.push(duration);
      if (resizeTimes.current.length > 100) {
        resizeTimes.current.shift();
      }

      const averageTime = resizeTimes.current.reduce((sum, t) => sum + t, 0) / resizeTimes.current.length;

      setMetrics(prev => ({
        ...prev,
        resizeCount: prev.resizeCount + 1,
        averageResizeTime: Math.round(averageTime * 100) / 100,
        lastResizeTime: Math.round(duration * 100) / 100,
      }));
    };
  }, []);

  const reset = React.useCallback(() => {
    setMetrics({
      fps: 60,
      resizeCount: 0,
      averageResizeTime: 0,
      lastResizeTime: 0,
    });
    fpsHistory.current = [];
    resizeTimes.current = [];
  }, []);

  return {
    metrics,
    trackResize,
    reset,
  };
};