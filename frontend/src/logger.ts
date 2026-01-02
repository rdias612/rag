/**
 * Sistema de logging centralizado para o frontend.
 * Envia logs ao backend para persistência em webserver.log.
 */

export const LogLevel = {
  DEBUG: "DEBUG",
  INFO: "INFO",
  WARNING: "WARNING",
  ERROR: "ERROR"
} as const;

export type LogLevel = typeof LogLevel[keyof typeof LogLevel];

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  component: string;
  message: string;
  data?: any;
}

class Logger {
  private component: string;
  private logQueue: LogEntry[] = [];
  private isFlushing: boolean = false;
  private flushInterval: number = 5000; // 5 segundos
  private maxQueueSize: number = 50;

  constructor(component: string) {
    this.component = component;
    // Iniciar flush automático
    setInterval(() => this.flush(), this.flushInterval);
    
    // Flush antes de fechar a página
    window.addEventListener('beforeunload', () => this.flushSync());
  }

  private createLogEntry(level: LogLevel, message: string, data?: any): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      component: this.component,
      message,
      data
    };
  }

  private logToConsole(entry: LogEntry) {
    const message = `[${entry.timestamp}] ${entry.level} ${entry.component} ${entry.message}`;
    switch (entry.level) {
      case LogLevel.DEBUG:
        console.debug(message, entry.data || '');
        break;
      case LogLevel.INFO:
        console.info(message, entry.data || '');
        break;
      case LogLevel.WARNING:
        console.warn(message, entry.data || '');
        break;
      case LogLevel.ERROR:
        console.error(message, entry.data || '');
        break;
    }
  }

  private addToQueue(entry: LogEntry) {
    this.logQueue.push(entry);
    
    // Flush imediato se a fila ficar muito grande
    if (this.logQueue.length >= this.maxQueueSize) {
      this.flush();
    }
  }

  /**
   * Envia logs ao backend de forma assíncrona
   */
  private async flush(): Promise<void> {
    if (this.isFlushing || this.logQueue.length === 0) {
      return;
    }

    this.isFlushing = true;
    const logsToSend = [...this.logQueue];
    this.logQueue = [];

    try {
      await fetch('/api/logs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ logs: logsToSend }),
      });
    } catch (error) {
      // Se falhar, volta os logs para a fila
      this.logQueue.unshift(...logsToSend);
      console.error('[Logger] Failed to send logs to backend:', error);
    } finally {
      this.isFlushing = false;
    }
  }

  /**
   * Flush síncrono para beforeunload (usa sendBeacon)
   */
  private flushSync() {
    if (this.logQueue.length === 0) return;

    const blob = new Blob(
      [JSON.stringify({ logs: this.logQueue })],
      { type: 'application/json' }
    );

    navigator.sendBeacon('/api/logs', blob);
    this.logQueue = [];
  }

  debug(message: string, data?: any) {
    const entry = this.createLogEntry(LogLevel.DEBUG, message, data);
    this.logToConsole(entry);
    this.addToQueue(entry);
  }

  info(message: string, data?: any) {
    const entry = this.createLogEntry(LogLevel.INFO, message, data);
    this.logToConsole(entry);
    this.addToQueue(entry);
  }

  warning(message: string, data?: any) {
    const entry = this.createLogEntry(LogLevel.WARNING, message, data);
    this.logToConsole(entry);
    this.addToQueue(entry);
  }

  error(message: string, error?: any) {
    const entry = this.createLogEntry(LogLevel.ERROR, message, error);
    this.logToConsole(entry);
    this.addToQueue(entry);
  }
}

/**
 * Cria um logger para um componente específico
 */
export function createLogger(component: string): Logger {
  return new Logger(component);
}
