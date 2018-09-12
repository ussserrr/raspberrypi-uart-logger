#ifndef LOGGING_H_
#define LOGGING_H_



#include <stdio.h>
#include "usart.h"


/*
 *  START edit these parameters to match your app
 */
#define LOG_BUF_SIZE 100  // in bytes
extern UART_HandleTypeDef huart1;
#define LOG_USART_TIMEOUT 0xFFFF
/*
 *  END edit these parameters to match your app
 */


char log_buf[LOG_BUF_SIZE];


enum log_msg_type {
	LOG_DEBUG,
	LOG_INFO,
	LOG_WARNING,
	LOG_ERROR,
	LOG_CRITICAL,

	LOG_NUM_OF_MSG_TYPES
};


extern int log_usart(char* log_msg, int msg_type);
extern void log_usart_is_present(void);
extern void log_logging_shutdown(void);



#endif /* LOGGING_H_ */
