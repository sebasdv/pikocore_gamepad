#include "LCD_1in3.h"
#include "DEV_Config.h"

#include <stdlib.h>		//itoa()
#include <stdio.h>

LCD_1IN3_ATTRIBUTES LCD_1IN3;


/******************************************************************************
function :	Hardware reset
parameter:
******************************************************************************/
static void LCD_1IN3_Reset(void)
{
    DEV_Digital_Write(EPD_RST_PIN, 1);
    DEV_Delay_ms(100);
    DEV_Digital_Write(EPD_RST_PIN, 0);
    DEV_Delay_ms(100);
    DEV_Digital_Write(EPD_RST_PIN, 1);
    DEV_Delay_ms(100);
}

/******************************************************************************
function :	send command
parameter:
     Reg : Command register
******************************************************************************/
static void LCD_1IN3_SendCommand(UBYTE Reg)
{
    DEV_Digital_Write(EPD_DC_PIN, 0);
    DEV_Digital_Write(EPD_CS_PIN, 0);
    DEV_SPI_WriteByte(Reg);
    DEV_Digital_Write(EPD_CS_PIN, 1);
}

/******************************************************************************
function :	send data
parameter:
    Data : Write data
******************************************************************************/
static void LCD_1IN3_SendData_8Bit(UBYTE Data)
{
    DEV_Digital_Write(EPD_DC_PIN, 1);
    DEV_Digital_Write(EPD_CS_PIN, 0);
    DEV_SPI_WriteByte(Data);
    DEV_Digital_Write(EPD_CS_PIN, 1);
}

/******************************************************************************
function :	send data
parameter:
    Data : Write data
******************************************************************************/
static void LCD_1IN3_SendData_16Bit(UWORD Data)
{
    DEV_Digital_Write(EPD_DC_PIN, 1);
    DEV_Digital_Write(EPD_CS_PIN, 0);
    DEV_SPI_WriteByte((Data >> 8) & 0xFF);
    DEV_SPI_WriteByte(Data & 0xFF);
    DEV_Digital_Write(EPD_CS_PIN, 1);
}

/******************************************************************************
function :	Initialize the lcd register
parameter:
******************************************************************************/
static void LCD_1IN3_InitReg(void)
{
    LCD_1IN3_SendCommand(0x11);              
    DEV_Delay_ms(120); 

    LCD_1IN3_SendCommand(0x3A); 
    LCD_1IN3_SendData_8Bit(0x05);


    LCD_1IN3_SendCommand(0xB2);
    LCD_1IN3_SendData_8Bit(0x1F);
    LCD_1IN3_SendData_8Bit(0x1F);
    LCD_1IN3_SendData_8Bit(0x00);
    LCD_1IN3_SendData_8Bit(0x33);
    LCD_1IN3_SendData_8Bit(0x33);

    LCD_1IN3_SendCommand(0xB7); 
    LCD_1IN3_SendData_8Bit(0x00); // VGH=12.2V,VGL=-7.16V 

    LCD_1IN3_SendCommand(0xBB);
    LCD_1IN3_SendData_8Bit(0x3F);

    LCD_1IN3_SendCommand(0xC0);
    LCD_1IN3_SendData_8Bit(0x2C);

    LCD_1IN3_SendCommand(0xC2);
    LCD_1IN3_SendData_8Bit(0x01);

    LCD_1IN3_SendCommand(0xC3);
    LCD_1IN3_SendData_8Bit(0x0f); //4.3V   

    LCD_1IN3_SendCommand(0xC4);
    LCD_1IN3_SendData_8Bit(0x20);  //VDV, 0x20:0v 

    LCD_1IN3_SendCommand(0xC6); 
    LCD_1IN3_SendData_8Bit(0x13);    

    LCD_1IN3_SendCommand(0xD0); 
    LCD_1IN3_SendData_8Bit(0xA4);
    LCD_1IN3_SendData_8Bit(0xA1);


    LCD_1IN3_SendCommand(0xE0);
    LCD_1IN3_SendData_8Bit(0xF0);
    LCD_1IN3_SendData_8Bit(0x06);
    LCD_1IN3_SendData_8Bit(0x0D);
    LCD_1IN3_SendData_8Bit(0x0B);
    LCD_1IN3_SendData_8Bit(0x0A);
    LCD_1IN3_SendData_8Bit(0x07);
    LCD_1IN3_SendData_8Bit(0x2E);
    LCD_1IN3_SendData_8Bit(0x43);
    LCD_1IN3_SendData_8Bit(0x45);
    LCD_1IN3_SendData_8Bit(0x38);
    LCD_1IN3_SendData_8Bit(0x14);
    LCD_1IN3_SendData_8Bit(0x13);
    LCD_1IN3_SendData_8Bit(0x25);
    LCD_1IN3_SendData_8Bit(0x29);

    LCD_1IN3_SendCommand(0xE1);
    LCD_1IN3_SendData_8Bit(0xF0);
    LCD_1IN3_SendData_8Bit(0x07);
    LCD_1IN3_SendData_8Bit(0x0A);
    LCD_1IN3_SendData_8Bit(0x08);
    LCD_1IN3_SendData_8Bit(0x07);
    LCD_1IN3_SendData_8Bit(0x23);
    LCD_1IN3_SendData_8Bit(0x2E);
    LCD_1IN3_SendData_8Bit(0x33);
    LCD_1IN3_SendData_8Bit(0x44);
    LCD_1IN3_SendData_8Bit(0x3A);
    LCD_1IN3_SendData_8Bit(0x16);
    LCD_1IN3_SendData_8Bit(0x17);
    LCD_1IN3_SendData_8Bit(0x26);
    LCD_1IN3_SendData_8Bit(0x2C);

    LCD_1IN3_SendCommand(0xE4); 
    LCD_1IN3_SendData_8Bit(0x1d);
    LCD_1IN3_SendData_8Bit(0x00); 
    LCD_1IN3_SendData_8Bit(0x00);

    LCD_1IN3_SendCommand(0x21); 
    DEV_Delay_ms(120); 

    LCD_1IN3_SendCommand(0x29); 


    LCD_1IN3_SendCommand(0x2c);
}

/********************************************************************************
function:	Set the resolution and scanning method of the screen
parameter:
		Scan_dir:   Scan direction
********************************************************************************/
static void LCD_1IN3_SetAttributes(UBYTE Scan_dir)
{
    //Get the screen scan direction
    LCD_1IN3.SCAN_DIR = Scan_dir;
    UBYTE MemoryAccessReg = 0x00;

    //Get GRAM and LCD width and height
    if(Scan_dir == HORIZONTAL) {
        LCD_1IN3.HEIGHT	= LCD_1IN3_HEIGHT;
        LCD_1IN3.WIDTH   = LCD_1IN3_WIDTH;
        MemoryAccessReg = 0X70;
    } else {
        LCD_1IN3.HEIGHT	= LCD_1IN3_WIDTH;
        LCD_1IN3.WIDTH   = LCD_1IN3_HEIGHT;
        MemoryAccessReg = 0X00;
    }

    // Set the read / write scan direction of the frame memory
    LCD_1IN3_SendCommand(0x36); //MX, MY, RGB mode
    LCD_1IN3_SendData_8Bit(MemoryAccessReg);	//0x08 set RGB
}

/********************************************************************************
function :	Initialize the lcd
parameter:
********************************************************************************/
void LCD_1IN3_Init(UBYTE Scan_dir)
{
    //Turn on the backlight
    // LCD_1IN3_BL_1;

    //Hardware reset
    LCD_1IN3_Reset();

    //Set the resolution and scanning method of the screen
    LCD_1IN3_SetAttributes(Scan_dir);
    
    //Set the initialization register
    LCD_1IN3_InitReg();
}

/********************************************************************************
function:	Sets the start position and size of the display area
parameter:
		Xstart 	:   X direction Start coordinates
		Ystart  :   Y direction Start coordinates
		Xend    :   X direction end coordinates
		Yend    :   Y direction end coordinates
********************************************************************************/
void LCD_1IN3_SetWindows(UWORD Xstart, UWORD Ystart, UWORD Xend, UWORD Yend)
{
    //set the X coordinates
    LCD_1IN3_SendCommand(0x2A);
    LCD_1IN3_SendData_8Bit((Xstart >> 8) & 0xFF);
    LCD_1IN3_SendData_8Bit(Xstart & 0xFF);
    LCD_1IN3_SendData_8Bit(((Xend  - 1) >> 8) & 0xFF);
    LCD_1IN3_SendData_8Bit((Xend  - 1) & 0xFF);

    //set the Y coordinates
    LCD_1IN3_SendCommand(0x2B);
    LCD_1IN3_SendData_8Bit((Ystart >> 8) & 0xFF);
    LCD_1IN3_SendData_8Bit(Ystart & 0xFF);
    LCD_1IN3_SendData_8Bit(((Yend  - 1) >> 8) & 0xFF);
    LCD_1IN3_SendData_8Bit((Yend  - 1) & 0xFF);

    LCD_1IN3_SendCommand(0X2C);
}

/******************************************************************************
function :	Clear screen
parameter:
******************************************************************************/
void LCD_1IN3_Clear(UWORD Color)
{
    UWORD j;
    UWORD Image[LCD_1IN3_WIDTH*LCD_1IN3_HEIGHT];
    
    Color = ((Color<<8)&0xff00)|(Color>>8);
   
    for (j = 0; j < LCD_1IN3_HEIGHT*LCD_1IN3_WIDTH; j++) {
        Image[j] = Color;
    }
    
    LCD_1IN3_SetWindows(0, 0, LCD_1IN3_WIDTH, LCD_1IN3_HEIGHT);
    DEV_Digital_Write(EPD_DC_PIN, 1);
    DEV_Digital_Write(EPD_CS_PIN, 0);
    for(j = 0; j < LCD_1IN3_HEIGHT; j++){
        DEV_SPI_Write_nByte((uint8_t *)&Image[j*LCD_1IN3_WIDTH], LCD_1IN3_WIDTH*2);
    }
    DEV_Digital_Write(EPD_CS_PIN, 1);
}

/******************************************************************************
function :	Sends the image buffer in RAM to displays
parameter:
******************************************************************************/
void LCD_1IN3_Display(UWORD *Image)
{
    UWORD j;
    LCD_1IN3_SetWindows(0, 0, LCD_1IN3_WIDTH, LCD_1IN3_HEIGHT);
    DEV_Digital_Write(EPD_DC_PIN, 1);
    DEV_Digital_Write(EPD_CS_PIN, 0);
    for (j = 0; j < LCD_1IN3_HEIGHT; j++) {
        DEV_SPI_Write_nByte((uint8_t *)&Image[j*LCD_1IN3_WIDTH], LCD_1IN3_WIDTH*2);
    }
    DEV_Digital_Write(EPD_CS_PIN, 1);
}

void LCD_1IN3_DisplayWindows(UWORD Xstart, UWORD Ystart, UWORD Xend, UWORD Yend, UWORD *Image)
{
    // display
    UDOUBLE Addr = 0;

    UWORD j;
    LCD_1IN3_SetWindows(Xstart, Ystart, Xend , Yend);
    DEV_Digital_Write(EPD_DC_PIN, 1);
    DEV_Digital_Write(EPD_CS_PIN, 0);
    // Upstream bug: SetWindows programs Yend-Ystart rows but this loop sent
    // one row less, leaving the last window row stale. Yend is exclusive.
    for (j = Ystart; j < Yend; j++) {
        Addr = Xstart + j * LCD_1IN3_WIDTH ;
        DEV_SPI_Write_nByte((uint8_t *)&Image[Addr], (Xend-Xstart)*2);
    }
    DEV_Digital_Write(EPD_CS_PIN, 1);
}

void LCD_1IN3_DisplayPoint(UWORD X, UWORD Y, UWORD Color)
{
    LCD_1IN3_SetWindows(X,Y,X,Y);
    LCD_1IN3_SendData_16Bit(Color);
}

