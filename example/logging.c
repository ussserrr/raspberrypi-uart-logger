#include "logging.h"


int log_usart(char *log_msg, int msg_type) {
	char msg_type_char = 'u';

	switch (msg_type) {
	case LOG_DEBUG:
		msg_type_char = 'D';
		break;
	case LOG_INFO:
		msg_type_char = 'I';
		break;
	case LOG_WARNING:
		msg_type_char = 'W';
		break;
	case LOG_ERROR:
		msg_type_char = 'E';
		break;
	case LOG_CRITICAL:
		msg_type_char = 'C';
		break;
	}

	int log_msg_size = snprintf(log_buf, LOG_BUF_SIZE, "%c %s\r", msg_type_char, log_msg);
	if ((log_msg_size<0) || (log_msg_size>LOG_BUF_SIZE)) {
		return -1;
	}

	HAL_UART_Transmit(&huart1, log_buf, log_msg_size, LOG_USART_TIMEOUT);

	return 0;
}


/*
 *  Call this function with timer
 */
void log_usart_is_present(void) {
	HAL_UART_Transmit(&huart1, "is_present\r", 11, LOG_USART_TIMEOUT);
}


/*
 *  Shutdown remote logging program
 */
void log_logging_shutdown(void) {
	HAL_UART_Transmit(&huart1, "end\r", 4, LOG_USART_TIMEOUT);
}
