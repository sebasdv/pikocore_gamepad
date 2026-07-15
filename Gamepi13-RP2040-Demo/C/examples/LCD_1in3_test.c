#include "LCD_Test.h"
#include "LCD_1in3.h"

bool reserved_addr(uint8_t addr) {
return (addr & 0x78) == 0 || (addr & 0x78) == 0x78;
}

int LCD_1in3_test(void)
{
    DEV_Delay_ms(100);
    printf("LCD_1in3_test Demo\r\n");
    if(DEV_Module_Init()!=0){
        return -1;
    }
    DEV_SET_PWM(50);
    /* LCD Init */
    printf("gamepi13 LCD demo...\r\n");
    LCD_1IN3_Init(HORIZONTAL);
    LCD_1IN3_Clear(WHITE);
    
    //LCD_SetBacklight(1023);
    UDOUBLE Imagesize = LCD_1IN3_HEIGHT*LCD_1IN3_WIDTH*2;
    UWORD *BlackImage;
    if((BlackImage = (UWORD *)malloc(Imagesize)) == NULL) {
        printf("Failed to apply for black memory...\r\n");
        exit(0);
    }
    // /*1.Create a new image cache named IMAGE_RGB and fill it with white*/
    Paint_NewImage((UBYTE *)BlackImage,LCD_1IN3.WIDTH,LCD_1IN3.HEIGHT, 0, WHITE);
    Paint_SetScale(65);
    Paint_Clear(WHITE);
    Paint_SetRotate(ROTATE_0);
    Paint_Clear(WHITE);
    
    // /* GUI */
    printf("drawing...\r\n");
    // /*2.Drawing on the image*/
#if 1
    Paint_SetRotate(ROTATE_270);
    Paint_DrawPoint(2,1, BLACK, DOT_PIXEL_1X1,  DOT_FILL_RIGHTUP);//240 240
    Paint_DrawPoint(2,6, BLACK, DOT_PIXEL_2X2,  DOT_FILL_RIGHTUP);
    Paint_DrawPoint(2,11, BLACK, DOT_PIXEL_3X3, DOT_FILL_RIGHTUP);
    Paint_DrawPoint(2,16, BLACK, DOT_PIXEL_4X4, DOT_FILL_RIGHTUP);
    Paint_DrawPoint(2,21, BLACK, DOT_PIXEL_5X5, DOT_FILL_RIGHTUP);
    Paint_DrawLine( 10,  5, 40, 35, MAGENTA, DOT_PIXEL_2X2, LINE_STYLE_SOLID);
    Paint_DrawLine( 10, 35, 40,  5, MAGENTA, DOT_PIXEL_2X2, LINE_STYLE_SOLID);

    Paint_DrawLine( 80,  20, 110, 20, CYAN, DOT_PIXEL_1X1, LINE_STYLE_DOTTED);
    Paint_DrawLine( 95,   5,  95, 35, CYAN, DOT_PIXEL_1X1, LINE_STYLE_DOTTED);

    Paint_DrawRectangle(10, 5, 40, 35, RED, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);
    Paint_DrawRectangle(45, 5, 75, 35, BLUE, DOT_PIXEL_2X2,DRAW_FILL_FULL);

    Paint_DrawCircle(95, 20, 15, GREEN, DOT_PIXEL_1X1, DRAW_FILL_EMPTY);
    Paint_DrawCircle(130, 20, 15, GREEN, DOT_PIXEL_1X1, DRAW_FILL_FULL);

    int  fade=250;
    pwm_set_gpio_level(EPD_BL_PIN, fade*fade);
    Paint_DrawNum (50, 40 ,123, &Font20,3,  WHITE,  BLACK);
    Paint_DrawString_EN(1, 40, "ABC", &Font20, 0x000f, 0xfff0);
    
    Paint_DrawString_EN(1, 100, "Waveshare", &Font16, RED, WHITE); 

    // /*3.Refresh the picture in RAM to LCD*/
    LCD_1IN3_Display(BlackImage);
    DEV_Delay_ms(3000);

#endif
#if 1 
     Paint_SetRotate(ROTATE_270);
     Paint_Clear(WHITE);
     Paint_DrawImage( gImage_12,0,0,240,240);
     LCD_1IN3_Display(BlackImage);
     DEV_Delay_ms(3000);
#endif
#if 1
     Paint_Clear(WHITE);
     Paint_DrawImage(gImage_11,0,0,240,240);
     LCD_1IN3_Display(BlackImage);
     DEV_Delay_ms(3000);

#endif

#if 1

    uint8_t A = 21; 
    uint8_t B = 20; 
    uint8_t X = 5; 
    uint8_t Y = 9;

    uint8_t up = 15;
    uint8_t down = 6;
    uint8_t left = 16;
    uint8_t right = 13;

    uint8_t select =19;
    uint8_t start = 26;
    uint8_t L = 23;
    uint8_t R = 4;
  

    SET_Infrared_PIN(A);    
    SET_Infrared_PIN(B);
    SET_Infrared_PIN(X);
    SET_Infrared_PIN(Y);
		 
	SET_Infrared_PIN(up);
    SET_Infrared_PIN(down);
    SET_Infrared_PIN(left);
    SET_Infrared_PIN(right);

    SET_Infrared_PIN(select);
    SET_Infrared_PIN(start);

    SET_Infrared_PIN(L);
    SET_Infrared_PIN(R);   

    Paint_Clear(WHITE);
    Paint_SetRotate(ROTATE_0);
    Paint_DrawRectangle(135, 3, 165,33, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);
    Paint_DrawRectangle(195,43,225,73, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);
    Paint_DrawRectangle(75, 43, 105, 73, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);
    Paint_DrawRectangle(135, 77, 165, 107, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);

    Paint_DrawRectangle(75, 167, 105, 197, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);
    Paint_DrawRectangle(195,167,225,197, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);
    Paint_DrawRectangle(135, 207,  165, 237, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);
    Paint_DrawRectangle(135, 133, 165, 163, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);

    Paint_DrawRectangle(15, 133, 45, 163, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);
    Paint_DrawRectangle(15, 3, 45, 33, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);

    Paint_DrawRectangle(15, 207, 45, 237, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);
    Paint_DrawRectangle(15, 77, 45, 107, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_EMPTY);
    LCD_1IN3_Display(BlackImage);
    LCD_1IN3_Display(BlackImage);

 
    while(1){

        if(DEV_Digital_Read(A) == 0){
            Paint_DrawRectangle(135, 3, 165,33,  0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(135, 3, 165,33, BlackImage);
            printf("gpio =%d\r\n",A);
        }
        else{
            Paint_DrawRectangle(135, 3, 165,33,  WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(135, 3, 165,33, BlackImage);
        }
            
        if(DEV_Digital_Read(B) == 0){
            Paint_DrawRectangle(195,43,225,73,0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(195,43,225,73,BlackImage);
            printf("gpio =%d\r\n",B);
        }
        else{
            Paint_DrawRectangle(195,43,225,73, WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(195,43,225,73,BlackImage);
        }
        
        if(DEV_Digital_Read(X) == 0){
            Paint_DrawRectangle(75, 43, 105, 73,  0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(75, 43, 105, 73, BlackImage);
            printf("gpio =%d\r\n",X);
        }
        else{
            Paint_DrawRectangle(75, 43, 105, 73,  WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(75, 43, 105, 73, BlackImage);
        }
            
        if(DEV_Digital_Read(Y ) == 0){
            Paint_DrawRectangle(135, 77, 165, 107,0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(135, 77, 165, 107,BlackImage);
            printf("gpio =%d\r\n",Y);
        }
        else{
            Paint_DrawRectangle(135, 77, 165, 107, WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(135, 77, 165, 107,BlackImage);
        }


        if(DEV_Digital_Read(up ) == 0){
            Paint_DrawRectangle(75, 167, 105, 197, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(75, 167, 105, 197, BlackImage);
            printf("gpio =%d\r\n",up);
        }
        else{
            Paint_DrawRectangle(75, 167, 105, 197, WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(75, 167, 105, 197,BlackImage);
        }

        if(DEV_Digital_Read(down ) == 0){
            Paint_DrawRectangle(195,167,225,197, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(195,167,225,197,BlackImage);
            printf("gpio =%d\r\n",down);
        }
        else{
            Paint_DrawRectangle(195,167,225,197, WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(195,167,225,197,BlackImage);
        }
        
        if(DEV_Digital_Read(left ) == 0){
            Paint_DrawRectangle(135, 207,  165, 237,  0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(135, 207,  165, 237, BlackImage);
            printf("gpio =%d\r\n",left);
        }
        else{
            Paint_DrawRectangle(135, 207,  165, 237, WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(135, 207,  165, 237, BlackImage);
        }
            
        if(DEV_Digital_Read(right ) == 0){
            Paint_DrawRectangle(135, 133, 165, 163, 0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(135, 133, 165, 163,BlackImage);
            printf("gpio =%d\r\n",right);
        }
        else{
            Paint_DrawRectangle(135, 133, 165, 163,WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(135, 133, 165, 163,BlackImage);
        }
        
        if(DEV_Digital_Read(select ) == 0){
            Paint_DrawRectangle(15, 133, 45, 163,0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(15, 133, 45, 163,BlackImage);
            printf("gpio =%d\r\n",select );
        }
        else{
            Paint_DrawRectangle(15, 133, 45, 163,WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(15, 133, 45, 163,BlackImage);
        }
        if(DEV_Digital_Read(start) == 0){
            Paint_DrawRectangle(15, 3, 45, 33,0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(15, 3, 45, 33,BlackImage);
            printf("gpio =%d\r\n",start );
        }
        else{
            Paint_DrawRectangle(15, 3, 45, 33, WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(15, 3, 45, 33,BlackImage);
        }


         if(DEV_Digital_Read(L)==0)
	{
            fade=fade+10;
            if ( fade>=250){fade=250;}
	    //fade=fade+10;
            sleep_ms(20);
            pwm_set_gpio_level(EPD_BL_PIN, fade*fade);
            Paint_DrawRectangle(15, 207, 45, 237,0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(15, 207, 45, 237,BlackImage);
           // printf("gpio =%d\r\n",L );
        }
        else{
            Paint_DrawRectangle(15, 207, 45, 237, WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(15, 207, 45, 237,BlackImage);

            }

        if(DEV_Digital_Read(R)==0){
            fade=fade-10;
            if ( fade<=0){fade=0;}
	    //fade=fade-10;
            sleep_ms(20);
           pwm_set_gpio_level(EPD_BL_PIN, fade*fade);
           Paint_DrawRectangle(15, 77, 45, 107,  0xF800, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(15, 77, 45, 107,  BlackImage);
         //   printf("gpio =%d\r\n",R );
        }
        else{
            Paint_DrawRectangle(15, 77, 45, 107, WHITE, DOT_PIXEL_2X2,DRAW_FILL_FULL);
            LCD_1IN3_DisplayWindows(15, 77, 45, 107,  BlackImage);
}

}
#endif

    /* Module Exit */
    free(BlackImage);
    BlackImage = NULL;
    
    DEV_Module_Exit();
    return 0;
}
